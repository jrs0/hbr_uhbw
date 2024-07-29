import argparse

# Keep this near the top otherwise help hangs
parser = argparse.ArgumentParser("icb_basic_results")
parser.add_argument(
    "-f",
    "--config-file",
    required=True,
    help="Specify the config file describing the model files that exist",
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

# Load all the models into memory
models = {}
for model in config["models"].keys():
    models[model] = common.load_item(f"{analysis_name}_{model}", save_dir=config["save_dir"])


# Loop over all the models creating the output graphs
for model_name, model_data in models.items():

    # These levels will define high risk for bleeding and ischaemia
    #
    # Various options are available for choosing this risk level:
    #
    # 1. Using established thresholds from the literature. For high
    #    bleeding risk, one such threshold is 4%, defined by the ARC
    #    HBR definition. (Need to find a similar concensus threshold
    #    for ischaemia risk.)
    # 2. Use the outcome prevalence in the training set. This would
    #    be an estimate of the observed average risk across the whole
    #    sample
    #
    # Currently option 2 is used below
    bleeding_threshold = model_data["y_test"]["bleeding"].mean()
    ischaemia_threshold = model_data["y_test"]["ischaemia"].mean()
    high_risk_thresholds = {
        "bleeding": bleeding_threshold,
        "ischaemia": ischaemia_threshold,
    }

    # Get the model
    fit_results = model_data["fit_results"]
    y_test = model_data["y_test"]

    model_abbr = config["models"][model_name]["abbr"]
    bleeding_abbr = config["outcomes"]["bleeding"]["abbr"]
    ischaemia_abbr = config["outcomes"]["ischaemia"]["abbr"]

    # Plot the ROC curves for the models
    fig, ax = plt.subplots(1, 2, figsize=figsize)
    for n, outcome in enumerate(["bleeding", "ischaemia"]):
        title = f"{outcome.title()} ROC Curves"
        roc_curves = fit_results["roc_curves"][outcome]
        roc_aucs = fit_results["roc_aucs"][outcome]
        roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
    plt.suptitle(
        f"ROC Curves for Models {model_abbr}-{bleeding_abbr} and {model_abbr}-{ischaemia_abbr}"
    )
    plt.tight_layout()
    plt.savefig(
        common.make_new_save_item_path(
            f"{analysis_name}_{model_name}_roc", config["save_dir"], "png"
        )
    )

    for outcome in ["bleeding", "ischaemia"]:

        outcome_abbr = config["outcomes"][outcome]["abbr"]

        # Plot the stability
        fig, ax = plt.subplots(1, 2, figsize=figsize)
        probs = fit_results["probs"]
        stability.plot_stability_analysis(
            ax, outcome, probs, y_test, high_risk_thresholds
        )
        plt.suptitle(
            f"Stability of {outcome.title()} Model {model_abbr}-{outcome_abbr}"
        )
        plt.tight_layout()
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_{model_name}_stability_{outcome}", config["save_dir"], "png"
            )
        )

        # Plot the calibrations
        fig, ax = plt.subplots(1, 2, figsize=figsize)
        calibrations = fit_results["calibrations"]
        calibration.plot_calibration_curves(ax[0], calibrations[outcome])
        calibration.draw_calibration_confidence(ax[1], calibrations[outcome][0])
        plt.suptitle(
            f"Calibration of {outcome.title()} Model {model_abbr}-{outcome_abbr}"
        )
        plt.tight_layout()
        plt.savefig(
            common.make_new_save_item_path(
                f"{analysis_name}_{model_name}_calibration_{outcome}", config["save_dir"], "png"
            )
        )

# Get the table of model summary metrics
summary = describe.get_summary_table(models, high_risk_thresholds, config)
common.save_item(summary, f"{analysis_name}_summary", config["save_dir"])

# Get the table of outcome prevalences
data = common.load_item(f"{analysis_name}_data", save_dir=config["save_dir"])
outcome_prevalences = describe.get_outcome_prevalence(data["outcomes"])
common.save_item(outcome_prevalences, f"{analysis_name}_outcome_prevalences", save_dir=config["save_dir"])

exit()

# Get prevalence of each outcome type
models[f"{analysis_name}_data"]["outcomes"][["bleeding", "ischaemia"]].sum()


model = "random_forest"
fit_results = models["fit_results"][model]
y_test = models["y_test"]
probs = fit_results["probs"]

outcome = "ischaemia"
pvalue = describe.pvalue_chi2_high_risk_vs_outcome(
    probs[outcome], y_test[outcome], high_risk_thresholds[outcome]
)
sig_level = 0.0001
print(f"Significant at {100*sig_level:.2f}% level: {pvalue < sig_level}")

# Want to create a contingency table between estimated bleeding/ischaemia
# risk quadrant and the observed outcomes

estimated_risk = pd.DataFrame(
    {
        "estimated_high_bleeding_risk": probs["bleeding"].iloc[:, 0]
        > high_risk_thresholds["bleeding"],
        "estimated_high_ischaemia_risk": probs["ischaemia"].iloc[:, 0]
        > high_risk_thresholds["ischaemia"],
    }
)

outcome = y_test[["bleeding", "ischaemia"]]

table = pd.crosstab(
    [
        estimated_risk["estimated_high_ischaemia_risk"],
        estimated_risk["estimated_high_bleeding_risk"],
    ],
    [outcome["ischaemia"], outcome["bleeding"]],
)

scipy.stats.chi2_contingency(table.to_numpy())
