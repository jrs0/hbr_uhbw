from typing import Any
from pandas import Series, DataFrame
import pandas as pd
import numpy as np

from pyhbr.analysis import roc
from pyhbr.analysis import stability
from pyhbr.analysis import calibration
from pyhbr import common


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
    model_names: dict[str, str],
    outcome_names: dict[str, str]
):
    """Get a table of model metric comparison across different models

    Args:
        models: Model saved data
    """
    names = []
    instabilities = []
    aucs = []
    risk_accuracy = []
    low_risk_reclass = []
    high_risk_reclass = []

    for model, fit_results in models["fit_results"].items():
        for outcome in ["bleeding", "ischaemia"]:
            names.append(f"{model_names[model]} ({outcome_names[outcome]})")

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
                    accuracy_mean += np.abs(all_calibrations["bin_center"].iloc[n] - all_calibrations["est_prev"].iloc[n])
                    
                    # When adding normal distributions together, the variances sum.
                    accuracy_variance += all_calibrations["est_prev_variance"].iloc[n]
                    
                    count += 1
            accuracy_mean /= count
            accuracy_variance /= count
            
            # Calculate a 95% confidence interval for the resulting mean of the accuracies,
            # assuming all the distributions are normal.
            ci_upper = accuracy_mean + 1.96*np.sqrt(accuracy_variance)
            ci_lower = accuracy_mean - 1.96*np.sqrt(accuracy_variance)
            risk_accuracy.append(f"{100*accuracy_mean:.2f}%, 95% CI [{100*ci_lower}%, {100*ci_upper}%]")

            threshold = high_risk_thresholds[outcome]
            y_test = models["y_test"][outcome]
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

    return DataFrame(
        {
            "Model": names,
            "Spread of Instability": instabilities,
            "P(H->L) > 50%": high_risk_reclass,
            "P(L->H) > 50%": low_risk_reclass,
            "Estimated Risk Accuracy": risk_accuracy,
            "ROC AUCs": aucs,
        }
    )
