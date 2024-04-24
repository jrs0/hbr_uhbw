from typing import Any

import matplotlib.pyplot as plt

from pyhbr import common
from pyhbr.analysis import roc
from pyhbr.analysis import stability
from pyhbr.analysis import calibration

import importlib

importlib.reload(stability)
importlib.reload(common)
importlib.reload(roc)

# Load the data
icb_basic_models = common.load_item("icb_basic_models")

# These levels will define high risk for bleeding and ischaemia
high_risk_thresholds = {
    "bleeding": 0.04,  # 4% from ARC HBR
    "ischaemia": 0.2,  # Could pick the median risk, or take from literature
}

# Get a model
model = "random_forest"
fit_results = icb_basic_models["fit_results"][model]
y_test = icb_basic_models["y_test"]

# Plot the ROC curves for the models
fig, ax = plt.subplots(1, 2)
for n, outcome in enumerate(["bleeding", "ischaemia"]):
    title = f"{outcome.title()} ROC Curves"
    roc_curves = fit_results["roc_curves"][outcome]
    roc_aucs = fit_results["roc_aucs"][outcome]
    roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
plt.tight_layout()
plt.show()

# Get the spread of the percentage-point errors and convert
# to a string

model_names = {
    "random_forest": "RF",
    "logistic_regression": "LR",
    "xgboost": "XGB",
}

outcome_names = {"bleeding": "B", "ischaemia": "I"}


def get_summary_table(models: dict[str, Any], high_risk_thresholds: dict[str, float]):
    """Get a table of model metric comparison across different models

    Args:
        models: Model saved data
    """
    names = []
    instabilities = []
    aucs = []
    inaccuracies = []
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

            absolute_errors = (
                100
                * (all_calibrations["bin_center"] - all_calibrations["est_prev"]).abs()
            )
            mean_accuracy = absolute_errors.mean()
            inaccuracies.append(f"{mean_accuracy:.2f}%")

            threshold = high_risk_thresholds[outcome]
            y_test = models["y_test"][outcome]
            df = stability.get_reclass_probabilities(
                probs[outcome], y_test, threshold
            )
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
            ).quantile([0.25, 0.5, 0.75])
            aucs.append(common.median_to_string(auc_spread, unit=""))

    return DataFrame(
        {
            "Model": names,
            "Median Instability": instabilities,
            "P(H->L) > 50%": high_risk_reclass,
            "P(L->H) > 50%": low_risk_reclass,
            "Estimated Mean Inaccuracy": inaccuracies,
            "ROC AUCs": aucs,
        }
    )


summary = get_summary_table(icb_basic_models, high_risk_thresholds)

# Plot the stability
outcome = "ischaemia"
fig, ax = plt.subplots(1, 2)
probs = fit_results["probs"]
stability.plot_stability_analysis(ax, outcome, probs, y_test, high_risk_thresholds)
plt.tight_layout()
plt.show()

# Plot the calibrations
outcome = "bleeding"
fig, ax = plt.subplots(1, 2)
calibrations = fit_results["calibrations"]
calibration.plot_calibration_curves(ax[0], calibrations[outcome])
calibration.draw_calibration_confidence(ax[1], calibrations[outcome][0])
plt.tight_layout()
plt.show()
