import importlib

import scipy
from numpy.random import RandomState
from sklearn.model_selection import train_test_split

from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from pyhbr import common

from pyhbr.analysis import model
from pyhbr.analysis import fit
from pyhbr.analysis import stability
from pyhbr.analysis import roc
from pyhbr.analysis import calibration
from pyhbr import common

import matplotlib.pyplot as plt

importlib.reload(model)
importlib.reload(calibration)
importlib.reload(common)
importlib.reload(stability)
importlib.reload(fit)

# Load outcome and training data
icb_basic_data = common.load_item("icb_basic_data")

# For convenience
outcomes = icb_basic_data["outcomes"]
features_index = icb_basic_data["features_index"]  # bool-only
features_codes = icb_basic_data["features_codes"]  # float-only
features_prescriptions = icb_basic_data["features_prescriptions"]  # float-only
features_measurements = icb_basic_data["features_measurements"]  # float-only
features_attributes = icb_basic_data["features_attributes"]  # float, category, Int8

# Combine all the features
features = (
    features_index.merge(features_codes, how="left", on="spell_id")
    .merge(features_prescriptions, how="left", on="spell_id")
    .merge(features_measurements, how="left", on="spell_id")
    .merge(features_attributes, how="left", on="spell_id")
)

# Convert to a binary outcome (rather than a count)
binary_outcome = outcomes > 0

# Create a random seed
random_state = RandomState(0)

# Create the train/test split
X_train, X_test, y_train, y_test = train_test_split(
    features, binary_outcome, test_size=0.5, random_state=random_state
)

# Using a larger number of bootstrap resamples will make
# the stability analysis better, but will take longer to fit.
num_bootstraps = 50

# Choose the number of bins for the calibration calculation.
# Using more bins will resolve the risk estimates more
# precisely, but will reduce the sample size in each bin for
# estimating the prevalence.
num_bins = 5

# Create a model to be trained on the preprocessed training set
# mod = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state)
mod = LogisticRegression(random_state=random_state)

# Make the preprocessing/fitting pipeline
pipe = model.make_random_forest(random_state, X_train)

# Fit the model, and also fit bootstrapped models (using resamples
# of the training set) to assess stability.
fit_results = fit.fit_model(
    pipe, X_train, y_train, X_test, y_test, num_bootstraps, num_bins, random_state
)

# Plot a tree from the forest
fig, ax = plt.subplots(1)
model.plot_random_forest(ax, fit_results, "bleeding", 3)
plt.show()

# These levels will define high risk for bleeding and ischaemia
high_risk_thresholds = {
    "bleeding": 0.04,  # 4% from ARC HBR
    "ischaemia": 0.2,  # Could pick the median risk, or take from literature
}

# Plot the ROC curves for the models
fig, ax = plt.subplots(1, 2)
for n, outcome in enumerate(["bleeding", "ischaemia"]):
    title = f"{outcome.title()} ROC Curves"
    roc_curves = fit_results["roc_curves"][outcome]
    roc_aucs = fit_results["roc_aucs"][outcome]
    roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
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
