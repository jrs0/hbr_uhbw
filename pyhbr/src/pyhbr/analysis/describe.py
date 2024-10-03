from typing import Any
from dataclasses import dataclass

from pandas import Series, DataFrame
import pandas as pd
import numpy as np
import scipy

from pyhbr.analysis import roc
from pyhbr.analysis import stability
from pyhbr.analysis import calibration
from pyhbr import common

from sksurv.nonparametric import kaplan_meier_estimator
import matplotlib.pyplot as plt
import seaborn as sns


def proportion_nonzero(column: Series) -> float:
    """Get the proportion of non-zero values in a column"""
    return (column > 0).sum() / len(column)


def get_column_rates(data: DataFrame) -> Series:
    """Get the proportion of rows in each column that are non-zero

    Either pass the full table, or subset it based
    on a condition to get the rates for that subset.

    Args:
        data: A table containing columns where the proportion
            of non-zero rows should be calculated.

    Returns:
        A Series (single column) with one row per column in the
            original data, containing the rate of non-zero items
            in each column. The Series is indexed by the names of
            the columns, with "_rate" appended.
    """
    return Series(
        {name + "_rate": proportion_nonzero(col) for name, col in data.items()}
    ).sort_values()


def column_prop(bool_col):
    """Return a string with the number of non-zero items in the columns
    and a percentage
    """
    count = bool_col.sum()
    percent = 100 * count / len(bool_col)
    return f"{count} ({percent:.2f}%)"


def proportion_missingness(data: DataFrame) -> Series:
    """Get the proportion of missing values in each column

    Args:
        data: A table where missingness should be calculate
            for each column

    Returns:
        The proportion of missing values in each column, indexed
            by the original table column name. The values are sorted
            in order of increasing missingness
    """
    return (data.isna().sum() / len(data)).sort_values().rename("missingness")


def nearly_constant(data: DataFrame, threshold: float) -> Series:
    """Check which columns of the input table have low variation

    A column is considered low variance if the proportion of rows
    containing NA or the most common non-NA value exceeds threshold.
    For example, if NA and one other value together comprise 99% of
    the column, then it is considered to be low variance based on
    a threshold of 0.9.

    Args:
        data: The table to check for zero variance
        threshold: The proportion of the column that must be NA or
            the most common value above which the column is considered
            low variance.

    Returns:
        A Series containing bool, indexed by the column name
            in the original data, containing whether the column
            has low variance.
    """

    def low_variance(column: Series) -> bool:

        if len(column) == 0:
            # If the column has length zero, consider
            # it low variance
            return True

        if len(column.dropna()) == 0:
            # If the column is all-NA, it is low variance
            # independently of the threshold
            return True

        # Else, if the proportion of NA and the most common
        # non-NA value is higher than threshold, the column
        # is low variance
        na_count = column.isna().sum()
        counts = column.value_counts()
        most_common_value_count = counts.iloc[0]
        if (na_count + most_common_value_count) / len(column) > threshold:
            return True

        return False

    return data.apply(low_variance).rename("nearly_constant")


def get_summary_table(
    models: dict[str, Any],
    high_risk_thresholds: dict[str, float],
    config: dict[str, Any],
):
    """Get a table of model metric comparison across different models

    Args:
        models: A map from model names to model data (containing the
            key "fit_results")
        high_risk_thresholds: A dictionary containing the keys
            "bleeding" and "ischaemia" mapped to the thresholds
            used to determine whether a patient is at high risk
            from the models.
        config: The config file used as input to the results and
            report generator scripts. It must contain the keys
            "outcomes" and "models", which are dictionaries
            containing the outcome or model name and a sub-key
            "abbr" which contains a short name of the outcome/model.
    """
    model_names = []
    instabilities = []
    aucs = []
    risk_accuracy = []
    low_risk_reclass = []
    high_risk_reclass = []
    model_key = []  # For identifying the model later
    outcome_key = []  # For identifying the outcome later
    median_auc = []  # Numerical AUC for finding the best model

    for model, model_data in models.items():
        for outcome in ["bleeding", "ischaemia"]:

            model_key.append(model)
            outcome_key.append(outcome)

            fit_results = model_data["fit_results"]

            # Abbreviated model name
            model_abbr = config["models"][model]["abbr"]
            outcome_abbr = config["outcomes"][outcome]["abbr"]
            model_names.append(f"{model_abbr}-{outcome_abbr}")

            probs = fit_results["probs"]

            # Get the summary instabilities
            instability = stability.average_absolute_instability(probs[outcome])
            instabilities.append(common.median_to_string(instability))

            # Get the summary calibration accuracies
            calibrations = fit_results["calibrations"][outcome]

            # Join together all the calibration data for the primary model
            # and all the bootstrap models, to compare the bin center positions
            # with the estimated prevalence for all bins.
            all_calibrations = pd.concat(calibrations)

            # Average relative error where prevalence is non-zero
            accuracy_mean = 0
            accuracy_variance = 0
            count = 0
            for n in range(len(all_calibrations)):
                if all_calibrations["est_prev"].iloc[n] > 0:

                    # This assumes that all risk predictions in the bin are at the bin center, with no
                    # distribution (i.e. the result is normal with a distribution based on the sample
                    # mean of the prevalence. For more accuracy, consider using the empirical distribution
                    # of the risk predictions in the bin as the basis for this calculation.
                    accuracy_mean += np.abs(
                        all_calibrations["bin_center"].iloc[n]
                        - all_calibrations["est_prev"].iloc[n]
                    )

                    # When adding normal distributions together, the variances sum.
                    accuracy_variance += all_calibrations["est_prev_variance"].iloc[n]

                    count += 1
            accuracy_mean /= count
            accuracy_variance /= count

            # Calculate a 95% confidence interval for the resulting mean of the accuracies,
            # assuming all the distributions are normal.
            ci_upper = accuracy_mean + 1.96 * np.sqrt(accuracy_variance)
            ci_lower = accuracy_mean - 1.96 * np.sqrt(accuracy_variance)
            risk_accuracy.append(
                f"{100*accuracy_mean:.2f}%, CI [{100*ci_lower:.2f}%, {100*ci_upper:.2f}%]"
            )

            threshold = high_risk_thresholds[outcome]
            y_test = model_data["y_test"][outcome]
            df = stability.get_reclass_probabilities(probs[outcome], y_test, threshold)
            high_risk = (df["original_risk"] >= threshold).sum()
            high_risk_and_unstable = (
                (df["original_risk"] >= threshold) & (df["unstable_prob"] >= 0.5)
            ).sum()
            high_risk_reclass.append(f"{100 * high_risk_and_unstable / high_risk:.2f}%")
            low_risk = (df["original_risk"] < threshold).sum()
            low_risk_and_unstable = (
                (df["original_risk"] < threshold) & (df["unstable_prob"] >= 0.5)
            ).sum()
            low_risk_reclass.append(f"{100 * low_risk_and_unstable / low_risk:.2f}%")

            # Get the summary ROC AUCs
            auc_data = fit_results["roc_aucs"][outcome]
            auc_spread = Series(
                auc_data.resample_auc + [auc_data.model_under_test_auc]
            ).quantile([0.025, 0.5, 0.975])
            aucs.append(common.median_to_string(auc_spread, unit=""))
            median_auc.append(auc_spread[0.5])

    return DataFrame(
        {
            "Model": model_names,
            "Spread of Instability": instabilities,
            "H→L": high_risk_reclass,
            "L→H": low_risk_reclass,
            "Estimated Risk Uncertainty": risk_accuracy,
            "ROC AUC": aucs,
            "model_key": model_key,
            "outcome_key": outcome_key,
            "median_auc": median_auc,
        }
    ).set_index("Model", drop=True)


def get_outcome_prevalence(outcomes: DataFrame) -> DataFrame:
    """Get the prevalence of each outcome as a percentage.

    This function takes the outcomes dataframe used to define
    the y vector of the training/testing set and calculates the
    prevalence of each outcome in a form suitable for inclusion
    in a report.

    Args:
        outcomes: A dataframe with the columns "fatal_{outcome}",
            "non_fatal_{outcome}", and "{outcome}" (for the total),
            where {outcome} is "bleeding" or "ischaemia". Each row
            is an index spell, and the elements in the table are
            boolean (whether or not the outcome occurred).

    Returns:
        A table with the prevalence of each outcome, and a multi-index
            containing the "Outcome" ("Bleeding" or "Ischaemia"), and
            the outcome "Type" (fatal, total, etc.)
    """
    df = (
        100
        * outcomes.rename(
            columns={
                "bleeding": "Bleeding.Total",
                "non_fatal_bleeding": "Bleeding.Non-Fatal (BARC 2-4)",
                "fatal_bleeding": "Bleeding.Fatal (BARC 5)",
                "ischaemia": "Ischaemia.Total",
                "non_fatal_ischaemia": "Ischaemia.Non-Fatal (MI/Stroke)",
                "fatal_ischaemia": "Ischaemia.Fatal (CV Death)",
            }
        )
        .melt(value_name="Prevalence (%)")
        .groupby("variable")
        .sum()
        / len(outcomes)
    )
    df = df.reset_index()
    df[["Outcome", "Type"]] = df["variable"].str.split(".", expand=True)
    return df.set_index(["Outcome", "Type"])[["Prevalence (%)"]].apply(
        lambda x: round(x, 2)
    )


def pvalue_chi2_high_risk_vs_outcome(
    probs: DataFrame, y_test: Series, high_risk_threshold: float
) -> float:
    """Perform a Chi-2 hypothesis test on the contingency between estimated high risk and outcome

    Get the p-value from the hypothesis test that there is no association
    between the estimated high-risk category, and the outcome. The p-value
    is interpreted as the probability of getting obtaining the outcomes
    corresponding to the model's estimated high-risk category under the
    assumption that there is no association between the two.

    Args:
        probs: The model-estimated probabilities (first column is used)
        y_test: Whether the outcome occurred
        high_risk_threshold: The cut-off risk (probability) defining an
            estimate to be high risk.

    Returns:
        The p-value for the hypothesis test.
    """

    # Get the cases (True) where the model estimated a risk
    # that puts the patient in the high risk category
    estimated_high_risk = (probs.iloc[:, 0] > high_risk_threshold).rename(
        "estimated_high_risk"
    )

    # Get the instances (True) in the test set where the outcome
    # occurred
    outcome_occurred = y_test.rename("outcome_occurred")

    # Create a contingency table of the estimated high risk
    # vs. whether the outcome occurred.
    table = pd.crosstab(estimated_high_risk, outcome_occurred)

    # Hypothesis test whether the estimated high risk category
    # is related to the outcome (null hypothesis is that there
    # is no relation).
    return scipy.stats.chi2_contingency(table.to_numpy()).pvalue


def plot_clinical_code_distribution(ax, data, config):
    """Plot histograms of the distribution of bleeding/ischaemia codes

    Args:
        ax: A list of two axes objects
        data: A loaded data file
        config: The analysis config (from yaml)
    """

    bleeding_group = config["outcomes"]["bleeding"]["non_fatal"]["group"]
    ischaemia_group = config["outcomes"]["ischaemia"]["non_fatal"]["group"]

    # Set the quantile level to find a cut-off that includes most codes
    level = 0.95

    codes = data["codes"]
    bleeding_codes = codes[codes["group"].eq(bleeding_group)]["position"]
    bleeding_codes.hist(ax=ax[0], rwidth=0.9)
    ax[0].set_title("Bleeding Codes")
    ax[0].set_xlabel("Code position (1 is primary, > 1 is secondary)")
    ax[0].set_ylabel("Total Code Count")

    q = bleeding_codes.quantile(level)
    ax[0].axvline(q)
    ax[0].text(
        q + 0.5,
        0.5,
        f"{100*level:.0f}% quantile",
        rotation=90,
        transform=ax[0].get_xaxis_transform(),
    )

    ischaemia_codes = codes[codes["group"].eq(ischaemia_group)]["position"]
    ischaemia_codes.hist(ax=ax[1], rwidth=0.9)
    ax[1].set_title("Ischaemia Codes")
    ax[1].set_xlabel("Code position")
    ax[1].set_ylabel("Total Code Count")

    q = ischaemia_codes.quantile(level)
    ax[1].axvline(q)
    ax[1].text(
        q + 0.5,
        0.5,
        f"{100*level:.0f}% quantile",
        rotation=90,
        transform=ax[1].get_xaxis_transform(),
    )

    plt.suptitle("Distribution of Bleeding/Ischaemia ICD-10 Primary/Secondary Codes")
    plt.tight_layout()


def plot_survival_curves(ax, data, config):
    """Plot survival curves for bleeding/ischaemia broken down by age

    Args:
        ax: A list of two axes objects
        data: A loaded data file
        config: The analysis config (from yaml)
    """

    # Mask the dataset by age to get different survival plots
    features_index = data["features_index"]
    print(features_index)
    age_over_75 = features_index["age"] > 75

    # Get bleeding survival data
    survival = data["bleeding_survival"].merge(
        features_index, on="spell_id", how="left"
    )

    # Calculate survival curves for bleeding (over 75)
    masked = survival[survival["age"] >= 75]
    status = ~masked["right_censor"]
    survival_in_days = masked["time_to_event"].dt.days
    time, survival_prob, conf_int = kaplan_meier_estimator(
        status, survival_in_days, conf_type="log-log"
    )
    ax[0].step(time, survival_prob, where="post", label="Age >= 75")
    ax[0].fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")

    # Now for under 75
    masked = survival[survival["age"] < 75]
    status = ~masked["right_censor"]
    survival_in_days = masked["time_to_event"].dt.days
    time, survival_prob, conf_int = kaplan_meier_estimator(
        status, survival_in_days, conf_type="log-log"
    )
    ax[0].step(time, survival_prob, where="post", label="Age < 75")
    ax[0].fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")

    ax[0].set_ylim(0.75, 1.00)
    ax[0].set_ylabel(r"Est. probability of no adverse event")
    ax[0].set_xlabel("Time (days)")
    ax[0].set_title("Bleeding Outcome")
    ax[0].legend()

    # Get ischaemia survival data
    survival = data["ischaemia_survival"].merge(
        features_index, on="spell_id", how="left"
    )

    # Calculate survival curves for ischaemia (over 75)
    masked = survival[survival["age"] >= 75]
    status = ~masked["right_censor"]
    survival_in_days = masked["time_to_event"].dt.days
    time, survival_prob, conf_int = kaplan_meier_estimator(
        status, survival_in_days, conf_type="log-log"
    )
    ax[1].step(time, survival_prob, where="post", label="Age >= 75")
    ax[1].fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")

    # Now for under 75
    masked = survival[survival["age"] < 75]
    status = ~masked["right_censor"]
    survival_in_days = masked["time_to_event"].dt.days
    time, survival_prob, conf_int = kaplan_meier_estimator(
        status, survival_in_days, conf_type="log-log"
    )
    ax[1].step(time, survival_prob, where="post", label="Age < 75")
    ax[1].fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")

    ax[1].set_ylim(0.75, 1.00)
    ax[1].set_ylabel(r"Est. probability of no adverse event")
    ax[1].set_xlabel("Time (days)")
    ax[1].set_title("Ischaemia Outcome")
    ax[1].legend()

    plt.tight_layout()


def plot_arc_hbr_survival(ax, data, config):
    """Plot survival curves for bleeding by ARC HBR score

    Args:
        ax: One axis object
        data: A loaded data file
        config: The analysis config (from yaml)
    """

    # Get bleeding survival data
    survival = data["bleeding_survival"]
    features_index = data["features_index"]
    arc_hbr_score = data["arc_hbr_score"]
    arc_hbr_score["score"] = pd.cut(
        data["arc_hbr_score"]["total_score"],
        [0, 1, 2, 100],
        labels=["Score = 0", "0 < Score <= 1", "Score > 1"],
        right=False,
    )

    def masked_survival(survival, mask):
        masked_survival = survival[mask]
        status = ~masked_survival["right_censor"]
        survival_in_days = masked_survival["time_to_event"].dt.days
        return kaplan_meier_estimator(status, survival_in_days, conf_type="log-log")

    def add_arc_survival(ax, arc_mask, label, color):
        time, survival_prob, conf_int = masked_survival(survival, arc_mask)

        ax[0].step(time, survival_prob, where="post", color=color)
        ax[0].fill_between(
            time,
            conf_int[0],
            conf_int[1],
            alpha=0.25,
            step="post",
            label=label,
            color=color,
        )

    df = (
        features_index[["therapy"]]
        .fillna("Missing")
        .merge(arc_hbr_score[["score"]], how="left", on="spell_id")
        .groupby(["therapy", "score"], as_index=False)
        .size()
    )
    df["score_sum"] = df.groupby("score")["size"].transform(sum)
    df["percent"] = 100 * df["size"] / df["score_sum"]
    print(df.sort_values(["score", "therapy"]))
    df = df.rename(
        columns={"therapy": "Therapy", "percent": "Percent", "score": "Score"}
    ).drop(columns=["size", "score_sum"])
    print(df)

    # Set custom order of therapy (least to most aggressive)
    df["Therapy"] = pd.Categorical(df["Therapy"], ["Single", "DAPT-AC", "DAPT-AP", "DAPT-AT", "Triple", "Missing"])
    df = df.sort_values("Therapy")

    # Plot the distribution of therapies
    sns.barplot(
        data=df,
        x="Therapy",
        y="Percent",
        hue="Score",
        ax=ax[1],
        palette={
            "Score = 0": "tab:green",
            "0 < Score <= 1": "tab:orange",
            "Score > 1": "tab:red",
        },
    )

    # Plot survival curves by ARC score
    arc_mask = arc_hbr_score["score"] == "Score = 0"
    add_arc_survival(ax, arc_mask, "Score = 0", "tab:green")
    arc_mask = arc_hbr_score["score"] == "0 < Score <= 1"
    add_arc_survival(ax, arc_mask, "0 < Score <= 1", "tab:orange")
    arc_mask = arc_hbr_score["score"] == "Score > 1"
    add_arc_survival(ax, arc_mask, "Score > 1", "tab:red")

    ax[0].set_ylim(0.90, 1.00)
    ax[0].set_ylabel(r"Est. probability of no adverse event")
    ax[0].set_xlabel("Time (days since index ACS admission)")
    ax[0].set_title("Bleeding outcome survival curves by ARC HBR score")
    ax[0].legend()
    
    #plt.legend()
