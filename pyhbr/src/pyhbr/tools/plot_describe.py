import argparse

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

    from pyhbr import common
    from pyhbr.analysis import roc
    from pyhbr.analysis import stability
    from pyhbr.analysis import calibration
    from pyhbr.analysis import describe
    from sksurv.nonparametric import kaplan_meier_estimator
    import seaborn as sns

    import importlib

    importlib.reload(stability)
    importlib.reload(common)
    importlib.reload(roc)
    importlib.reload(describe)

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

    # This is used to load a file, and is also used
    # as the prefix for all saved data files.
    analysis_name = config["analysis_name"]
    
    print(f"Analysis name: {analysis_name}")
    
    # Load the data from file
    data, data_path = common.load_item(f"{analysis_name}_data", save_dir=config["save_dir"])
    
    print(data.keys())
    
    # Plot the ROC curves for the models
    fig, ax = plt.subplots(1, 2, figsize=figsize)
    
    # Calculate survival curves for bleeding
    survival = data["bleeding_survival"]
    status = ~survival["right_censor"]
    survival_in_days = survival["time_to_event"].dt.days
    time, survival_prob, conf_int = kaplan_meier_estimator(
        status, survival_in_days, conf_type="log-log"
    )
    
    ax[0].step(time, survival_prob, where="post")
    ax[0].fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")
    ax[0].set_ylim(0.85, 1.00)
    ax[0].set_ylabel(r"Est. probability of no adverse event")
    ax[0].set_xlabel("Time (days)")
    ax[0].set_title("Bleeding Outcome")
    
    # Calculate survival curves for ischaemia
    survival = data["ischaemia_survival"]
    status = ~survival["right_censor"]
    survival_in_days = survival["time_to_event"].dt.days
    time, survival_prob, conf_int = kaplan_meier_estimator(
        status, survival_in_days, conf_type="log-log"
    )
    
    ax[1].step(time, survival_prob, where="post")
    ax[1].fill_between(time, conf_int[0], conf_int[1], alpha=0.25, step="post")
    ax[1].set_ylim(0.85, 1.00)
    ax[1].set_ylabel(r"Est. probability of no adverse event")
    ax[1].set_xlabel("Time (days)")
    ax[1].set_title("Ischaemia Outcome")    
    
    plt.tight_layout()
    
    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_survival", config["save_dir"], "png"
            )
        )
    
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
    ax[0].tick_params(axis='x', rotation=45)
    
    # Plot numeric attributes
    long = numeric_attributes.melt(var_name="Numeric Feature", value_name="Numeric Value")
    sns.histplot(long, x="Numeric Value", hue="Numeric Feature", ax=ax[1])
    ax[1].set_title("Other numerical non-missing primary care attributes")
    ax[1].set_xlim(0, 100)
    ax[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    if args.plot:
        plt.show()
    else:
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_attributes", config["save_dir"], "png"
            )
        )