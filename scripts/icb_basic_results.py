import matplotlib.pyplot as plt
from pyhbr import common
from pyhbr.analysis import roc
from pyhbr.analysis import stability

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

# Plot the ROC curves for the models
fig, ax = plt.subplots(1, 2)
for n, outcome in enumerate(["bleeding", "ischaemia"]):
    title = f"{outcome.title()} ROC Curves"
    roc_curves = fit_results["roc_curves"][outcome]
    roc_aucs = fit_results["roc_aucs"][outcome]
    roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
plt.tight_layout()
plt.show()

# Plot the stability
outcome = "bleeding"
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
