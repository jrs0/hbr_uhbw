import importlib

import scipy
from numpy.random import RandomState
from sklearn.model_selection import train_test_split

from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from pyhbr import common

from pyhbr.analysis import model
from pyhbr.analysis import stability
from pyhbr.analysis import roc
from pyhbr.analysis import calibration
from pyhbr import common

import matplotlib.pyplot as plt

importlib.reload(model)
importlib.reload(calibration)
importlib.reload(common)
importlib.reload(stability)

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

# Make all the preprocessors for each group of columns
preprocessors = [
    model.make_category_preprocessor(X_train),
    model.make_flag_preprocessor(X_train),
    model.make_float_preprocessor(X_train),
]

# Combine the preprocessors together into a column transformer
# which performs the preprocessing on the groups of columns in
# parallel.
preprocess = model.make_columns_transformer(preprocessors)

# Create a model to be trained on the preprocessed training set
mod = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state)

pipe = Pipeline([("preprocess", preprocess), ("model", mod)])

# Fit the bleeding and ischaemia models on the training set
# and bootstrap resamples of the training set (to assess stability)
fitted_models = {
    "bleeding": stability.fit_model(
        pipe, X_train, y_train.loc[:, "bleeding"], 50, random_state
    ),
    "ischaemia": stability.fit_model(
        pipe, X_train, y_train.loc[:, "ischaemia"], 50, random_state
    ),
}

# Calculate the results of the model
probs = {}
calibrations = {}
roc_curves = {}
roc_aucs = {}
for outcome in ["bleeding", "ischaemia"]:

    # Get the predicted probabilities associated with all the resamples of
    # the bleeding and ischaemia models
    probs[outcome] = stability.predict_probabilities(fitted_models[outcome], X_test)

    # Get the calibration of the models
    num_bins = 5
    calibrations[outcome] = calibration.get_variable_width_calibration(
        probs[outcome], y_test.loc[:, outcome], num_bins
    )

    # Calculate the ROC curves for the models
    roc_curves[outcome] = roc.get_roc_curves(probs[outcome], y_test.loc[:, outcome])
    roc_aucs[outcome] = roc.get_auc(probs[outcome], y_test.loc[:, outcome])

high_risk_thresholds = {
    "bleeding": 0.04,  # 4% from ARC HBR
    "ischaemia": 0.2,  # Could pick the median risk, or take from literature
}

# Plot the ROC curves for the models
fig, ax = plt.subplots(1, 2)
roc.plot_roc_curves(
    ax[0], roc_curves["bleeding"], roc_aucs["bleeding"], "Bleeding ROC Curves"
)
roc.plot_roc_curves(
    ax[1], roc_curves["ischaemia"], roc_aucs["ischaemia"], "Ischaemia ROC Curves"
)
plt.show()

# Plot the stability
fig, ax = plt.subplots(1, 2)
stability.plot_stability_analysis(ax, "bleeding", probs, y_test, high_risk_thresholds)
plt.tight_layout()
plt.show()

# Plot the calibrations
outcome_name = "bleeding"
fig, ax = plt.subplots(1, 2)
calibration.plot_calibration_curves(ax[0], calibrations[outcome_name])
calibration.draw_calibration_confidence(ax[1], calibrations[outcome_name][0])
plt.tight_layout()
plt.show()
