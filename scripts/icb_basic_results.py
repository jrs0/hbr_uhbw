import matplotlib.pyplot as plt

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

# Folder in which to save plots and other data
res_folder = "../hbr_papers/resources/"

# Load the data
icb_basic_models = common.load_item("icb_basic_models")

# These levels will define high risk for bleeding and ischaemia
high_risk_thresholds = {
    "bleeding": 0.04,  # 4% from ARC HBR
    "ischaemia": 0.2,  # Could pick the median risk, or take from literature
}

# Map the model names to strings for the report
model_names = {
    "random_forest": "RF",
    "logistic_regression": "LR",
    "xgboost": "XGB",
}

# Map the outcome names to strings for the report
outcome_names = {"bleeding": "B", "ischaemia": "I"}

names = describe.Names(model_names, outcome_names)

# Set the aspect ratio for the figures to roughly 2:1,
# because each plot is two graphs side-by-side
figsize=(11,5)

# Loop over all the models
for model in model_names.keys():
    
    # Get the model
    fit_results = icb_basic_models["fit_results"][model]
    y_test = icb_basic_models["y_test"]

    # Plot the ROC curves for the models
    fig, ax = plt.subplots(1, 2, figsize=figsize)
    for n, outcome in enumerate(["bleeding", "ischaemia"]):
        title = f"{outcome.title()} ROC Curves"
        roc_curves = fit_results["roc_curves"][outcome]
        roc_aucs = fit_results["roc_aucs"][outcome]
        roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
    plt.suptitle(f"ROC Curves for Models {names.model_name(model, 'bleeding')} and {names.model_name(model, 'ischaemia')}")
    plt.tight_layout()
    plt.savefig(res_folder + f"roc_{model}.png")

    for outcome in ["bleeding", "ischaemia"]:
        
        # Plot the stability
        fig, ax = plt.subplots(1, 2, figsize=figsize)
        probs = fit_results["probs"]
        stability.plot_stability_analysis(ax, outcome, probs, y_test, high_risk_thresholds)
        plt.suptitle(f"Stability of {outcome.title()} Model {names.model_name(model, outcome)}")
        plt.tight_layout()
        plt.savefig(res_folder + f"stability_{model}_{outcome}.png")
        
        # Plot the calibrations
        fig, ax = plt.subplots(1, 2, figsize=figsize)
        calibrations = fit_results["calibrations"]
        calibration.plot_calibration_curves(ax[0], calibrations[outcome])
        calibration.draw_calibration_confidence(ax[1], calibrations[outcome][0])
        plt.suptitle(f"Calibration of {outcome.title()} Model {names.model_name(model, outcome)}")
        plt.tight_layout()
        plt.savefig(res_folder + f"calibration_{model}_{outcome}.png")

# Get the table of model summary metrics
summary = describe.get_summary_table(icb_basic_models, high_risk_thresholds, names)
with open(res_folder + "summary.tex", 'w') as f:
     f.write(summary.to_latex())



