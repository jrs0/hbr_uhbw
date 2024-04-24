import importlib

import scipy
from numpy.random import RandomState
from sklearn.model_selection import train_test_split

from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

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

# Make the preprocessing/fitting pipeline
pipe = model.make_random_forest(random_state, X_train)
#pipe = model.make_logistic_regression(random_state, X_train)
#pipe = model.make_xgboost(random_state, X_train)

# Fit the model, and also fit bootstrapped models (using resamples
# of the training set) to assess stability.
fit_results = fit.fit_model(
    pipe, X_train, y_train, X_test, y_test, num_bootstraps, num_bins, random_state
)

# Process the dataset
model.get_features(fit_results["fitted_models"]["bleeding"].M0, X_train).mean().sort_values()

# Plot a tree from the forest
fig, ax = plt.subplots(1)
model.plot_random_forest(ax, fit_results, "bleeding", 3)
plt.show()

# Plot the ROC curves for the models
fig, ax = plt.subplots(1, 2)
for n, outcome in enumerate(["bleeding", "ischaemia"]):
    title = f"{outcome.title()} ROC Curves"
    roc_curves = fit_results["roc_curves"][outcome]
    roc_aucs = fit_results["roc_aucs"][outcome]
    roc.plot_roc_curves(ax[n], roc_curves, roc_aucs, title)
plt.tight_layout()
plt.show()

# These levels will define high risk for bleeding and ischaemia
high_risk_thresholds = {
    "bleeding": 0.04,  # 4% from ARC HBR
    "ischaemia": 0.2,  # Could pick the median risk, or take from literature
}

# Plot the stability
outcome = "bleeding"
fig, ax = plt.subplots(1, 2)
probs = fit_results["probs"]


n_bins = 5
probs = fit_results["probs"]["bleeding"]
ordered = probs.sort_values("prob_M0")
rows_per_bin = int(np.ceil(len(ordered) / n_bins))

# Get the mean and range of each bin 
bin_center = []
bin_width = []
for start in range(0, len(ordered), rows_per_bin):
    end = start + rows_per_bin
    bin_probs = ordered.iloc[start:end, 0]
    upper = bin_probs.max()
    lower = bin_probs.min()
    bin_center.append(100*(lower + upper) / 2)
    bin_width.append(90*(upper - lower))

# Get the other model's risk predictions
bins = []
for start in range(0, len(ordered), rows_per_bin):
    end = start + rows_per_bin
    bootstrap_probs = ordered.iloc[start:end, :]
    
    # Make a table containing the initial risk (from the
    # model under test) and a column for all other risks
    prob_compare = bootstrap_probs.melt(id_vars="prob_M0", value_name="bootstrap_risk", var_name="initial_risk")
    
    
    # Round the resulting risk error to 2 decimal places (i.e. to 0.01%). This truncates very small values
    # to zero, which means the resulting log y scale is not artificially extended downwards.
    absolute_error = (prob_compare["bootstrap_risk"] - prob_compare["prob_M0"]).abs().round(decimals=2)
    
    bins.append(100*absolute_error)

other_predictions = pd.concat(bins, axis=1)

fig, ax = plt.subplots(1)
ax.boxplot(other_predictions, positions=bin_center, widths=bin_width, whis=(0,100))
ax.set_yscale("log")
ax.set_xscale("log")
ax.set_ylim([0.01, 100])
ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=1))
ax.set_ylabel("Absolute difference in estimate from bootstrap")
ax.set_xlabel("Model-estimated risks")
plt.tight_layout()
plt.show()

#stability.plot_stability_analysis(ax, outcome, probs, y_test, high_risk_thresholds)
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
