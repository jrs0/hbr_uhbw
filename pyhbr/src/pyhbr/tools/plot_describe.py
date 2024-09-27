import argparse
from loguru import logger as log
import matplotlib.pyplot as plt
from pyhbr import common


def plot_or_save(plot: bool, name: str, save_dir: str):
    """Plot the graph interactively or save the figure

    Args:
        plot: If true, plot interactively and don't save. Otherwise, save
        name: The filename (without the .png) to save the figure has
        save_dir: The directory in which to save the figure
    """
    if plot:
        log.info(f"Plotting {name}, not saving")
        plt.show()
    else:
        log.info(f"Saving figure {name} in {save_dir}")
        plt.savefig(common.make_new_save_item_path(name, save_dir, "png"))


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
    import pickle

    from pyhbr import common
    from pyhbr.analysis import roc
    from pyhbr.analysis import stability
    from pyhbr.analysis import calibration
    from pyhbr.analysis import describe
    from sksurv.nonparametric import kaplan_meier_estimator
    import seaborn as sns
    import matplotlib.transforms as transforms

    # Load the config file
    config = common.read_config_file(args.config_file)
    analysis_name = config["analysis_name"]
    save_dir = config["save_dir"]
    now = common.current_timestamp()

    # Set up the log file output for plot/describe script
    log_file = (
        Path(save_dir) / Path(analysis_name + f"_plot_describe_{now}")
    ).with_suffix(".log")
    log_format = "{time} {level} {message}"
    log_id = log.add(log_file, format=log_format)

    # Set the aspect ratio for the figures to roughly 2:1,
    # because each plot is two graphs side-by-side
    figsize = (11, 5)

    log.info(f"Starting plot/describe script")
    data, raw_data, data_path = common.load_most_recent_data_files(
        analysis_name, save_dir
    )

    df = data["non_fatal_bleeding"]
    log.info(f"The maximum ischaemia secondary seen was {df['position'].max()}")

    df = data["non_fatal_ischaemia"]
    log.info(f"The maximum ischaemia secondary seen was {df['position'].max()}")

    # Plot the distribution of code positions for bleeding/ischaemia codes
    fig, ax = plt.subplots(1, 2, figsize=figsize)
    describe.plot_clinical_code_distribution(ax, data, config)
    plot_or_save(args.plot, f"{analysis_name}_codes_hist", save_dir)

    # Plot the bleeding/ischaemia survival curves broken down by age
    fig, ax = plt.subplots(1, 2, figsize=figsize)
    describe.plot_survival_curves(ax, data, config)
    plot_or_save(args.plot, f"{analysis_name}_survival", save_dir)

    # Plot the bleeding survival curves by ARC HBR score
    fig, ax = plt.subplots()
    describe.plot_arc_hbr_survival(ax, data, config)
    plot_or_save(args.plot, f"{analysis_name}_arc_survival", save_dir)

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

    plot_or_save(args.plot, f"{analysis_name}_primary_care_measurements", save_dir)

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
    plot_or_save(args.plot, f"{analysis_name}_attributes", save_dir)
