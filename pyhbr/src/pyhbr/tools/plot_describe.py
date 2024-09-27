import argparse
from loguru import logger as log


def main():

    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser("plot-describe")
    parser.add_argument(
        "-f",
        "--config-file",
        required=True,
        help="Specify the config file describing the analysis to run",
    )
    parser.add_argument(
        "-p",
        "--plot",
        help="Plot figures instead of saving them",
        action="store_true",
    )
    args = parser.parse_args()

    from pathlib import Path
    import pandas as pd
    import matplotlib.pyplot as plt
    import scipy
    import yaml
    import pickle

    from pyhbr import common
    from pyhbr.analysis import roc
    from pyhbr.analysis import stability
    from pyhbr.analysis import calibration
    from pyhbr.analysis import describe
    from sksurv.nonparametric import kaplan_meier_estimator
    import seaborn as sns
    import matplotlib.transforms as transforms

    # Read the configuration file
    with open(args.config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Failed to load config file: {exc}")
            exit(1)

    # Set the aspect ratio for the figures to roughly 2:1,
    # because each plot is two graphs side-by-side
    figsize = (11, 5)

    analysis_name = config["analysis_name"]
    save_dir = config["save_dir"]
    now = common.current_timestamp()

    # Set up the log file output for plot/describe script
    log_file = (
        Path(save_dir) / Path(analysis_name + f"_plot_describe_{now}")
    ).with_suffix(".log")
    log_format = "{time} {level} {message}"
    log_id = log.add(log_file, format=log_format)

    log.info(f"Starting plot/describe script")

    item_name = f"{analysis_name}_data"
    log.info(f"Loading most recent data file '{item_name}'")
    data, data_path = common.load_item(item_name, save_dir=save_dir)

    raw_file = data["raw_file"]
    log.info(f"Loading the underlying raw data file '{raw_file}'")
    raw_data = common.load_exact_item(raw_file, save_dir=save_dir)

    print(f"Items in the data file {data.keys()}")
    print(f"Items in the raw data file {raw_file}: {raw_data.keys()}")

    # Print a snapshot of the non-fatal results
    df = data["non_fatal_bleeding"]
    print("Snapshot of non-fatal bleeding outcomes")
    print(df)
    print(f"The maximum secondary seen was {df['position'].max()}")

    df = data["non_fatal_ischaemia"]
    print("Snapshot of non-fatal ischaemia outcomes")
    print(df)
    print(f"The maximum secondary seen was {df['position'].max()}")

    # Plot the distribution of code positions for bleeding/ischaemia codes
    fig, ax = plt.subplots(1, 2, figsize=figsize)

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

    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_codes_hist", config["save_dir"], "png"
            )
        )

    # Plot the ROC curves for the models
    fig, ax = plt.subplots(1, 2, figsize=figsize)

    # Mask the dataset by age to get different survival plots
    features_index = data["features_index"]
    print(features_index)
    age_over_75 = features_index["age"] > 75

    # Get bleeding survival data
    survival = (
        data["bleeding_survival"]
        .merge(features_index, on="spell_id", how="left")
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

    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_survival", config["save_dir"], "png"
            )
        )

    def masked_survival(survival, mask):
        masked_survival = survival[mask]
        status = ~masked_survival["right_censor"]
        survival_in_days = masked_survival["time_to_event"].dt.days
        return kaplan_meier_estimator(
            status, survival_in_days, conf_type="log-log"
        )

    def add_arc_survival(ax, arc_mask, label):
        time, survival_prob, conf_int = masked_survival(survival, arc_mask)

        ax.step(time, survival_prob, where="post")
        ax.fill_between(
            time, conf_int[0], conf_int[1], alpha=0.25, step="post", label=label
        )
    
    # Plot survival curves by ARC score
    fig, ax = plt.subplots()
    arc_mask = data["arc_hbr_score"]["total_score"] == 0
    add_arc_survival(ax, arc_mask, "Score = 0.0")
    arc_mask = data["arc_hbr_score"]["total_score"] == 1
    add_arc_survival(ax, arc_mask, "Score = 1.0")
    arc_mask = data["arc_hbr_score"]["total_score"] == 2
    add_arc_survival(ax, arc_mask, "Score = 2.0")
    arc_mask = data["arc_hbr_score"]["total_score"] >= 3
    add_arc_survival(ax, arc_mask, "Score >= 3.0")
    
    ax.set_ylim(0.70, 1.00)
    ax.set_ylabel(r"Est. probability of no adverse event")
    ax.set_xlabel("Time (days)")
    ax.set_title("Bleeding outcome survival curves by ARC HBR score")
    plt.legend()
    
    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_arc_survival", config["save_dir"], "png"
            )
        )
    exit()

    # Plot measurement distribution
    features_measurements = data["features_measurements"]
    measurement_names = {
        "bp_systolic": "Blood pressure (sys.), mmHg",
        "bp_diastolic": "Blood pressure (dia.), mmHg",
        "hba1c": "HbA1c, mmol/mol",
    }
    long = features_measurements.rename(columns=measurement_names).melt(
        var_name="Measurement", value_name="Result"
    )
    sns.displot(long, x="Result", hue="Measurement")
    plt.title("Non-missing primary-care measurements (up to 2 months before index)")
    plt.tight_layout()

    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_primary_care_measurements", config["save_dir"], "png"
            )
        )

    # Plot some of these individually
    fig, ax = plt.subplots(1, 2, figsize=figsize)
    features_attributes = data["features_attributes"]
    numeric_names = {
        "egfr": "eGFR",
        "polypharmacy_repeat": "Pharm. (Rep.)",
        "polypharmacy_acute": "Pharm. (Acute)",
        "bmi": "BMI",
        "alcohol_units": "Alcohol",
        "efi_category": "EFI",
    }
    numeric_attributes = features_attributes.select_dtypes(include="float").rename(
        columns=numeric_names
    )
    missing_numeric = describe.proportion_missingness(numeric_attributes).rename(
        "Percent Missingness"
    )
    sns.barplot(100 * missing_numeric, ax=ax[0])
    ax[0].set_xlabel("Feature name")
    ax[0].set_title("Proportion of missingness in numerical attributes")
    ax[0].tick_params(axis="x", rotation=45)

    # Plot numeric attributes
    long = numeric_attributes.melt(
        var_name="Numeric Feature", value_name="Numeric Value"
    )
    sns.histplot(long, x="Numeric Value", hue="Numeric Feature", ax=ax[1])
    ax[1].set_title("Other numerical non-missing primary care attributes")
    ax[1].set_xlim(0, 100)
    ax[1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_attributes", config["save_dir"], "png"
            )
        )
