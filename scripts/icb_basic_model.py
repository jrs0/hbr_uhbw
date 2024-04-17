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
    features, binary_outcome, test_size=0.25, random_state=random_state
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

# Get the predicted probabilities associated with all the resamples of
# the bleeding and ischaemia models
probs = {
    "bleeding": stability.predict_probabilities(fitted_models["bleeding"], X_test),
    "ischaemia": stability.predict_probabilities(fitted_models["ischaemia"], X_test),
}

high_risk_thresholds = {
    "bleeding": 0.04,  # 4% from ARC HBR
    "ischaemia": 0.2,  # Could pick the median risk, or take from literature
}

# Plot the stability of predicted probabilities
outcome_name = "bleeding"
fig, ax = plt.subplots(1, 2)
stability.plot_instability(
    ax[0],
    probs[outcome_name],
    y_test.loc[:, outcome_name],
    "Stability of repeat risk prediction",
)
stability.plot_reclass_instability(
    ax[1],
    probs[outcome_name],
    y_test.loc[:, outcome_name],
    high_risk_thresholds[outcome_name],
)
plt.tight_layout()
plt.show()

# Calculate the ROC curves for the models
roc_curves = {
    "bleeding": roc.get_roc_curves(probs["bleeding"], y_test.loc[:, "bleeding"]),
    "ischaemia": roc.get_roc_curves(probs["ischaemia"], y_test.loc[:, "ischaemia"]),
}

roc_aucs = {
    "bleeding": roc.get_auc(probs["bleeding"], y_test.loc[:, "bleeding"]),
    "ischaemia": roc.get_auc(probs["ischaemia"], y_test.loc[:, "ischaemia"]),
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

# Get the calibration of the models
calibrations = {
    "bleeding": calibration.get_variable_width_calibration(
        probs["bleeding"], y_test.loc[:, "bleeding"], 5
    ),
    "ischaemia": calibration.get_variable_width_calibration(
        probs["ischaemia"], y_test.loc[:, "ischaemia"], 5
    ),
}

# Plot the calibrations
outcome_name = "bleeding"
fig, ax = plt.subplots(1, 2)
calibration.plot_calibration_curves(ax[0], calibrations[outcome_name])
calibration.draw_calibration_confidence(ax[1], calibrations[outcome_name][0])
plt.tight_layout()
plt.show()

# View the features that go directly into the model. This dataframe
# has the column that the model sees (after the preprocessing steps).
F_train = model.get_features(fit, X_train)

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test.loc[:, outcome_name], probs[:, 1])
auc

sns.displot(probs.iloc[2, :])
plt.show()


################# DRAFT


X_prep_fit = col_transformer.fit(X_train)
X_prep = X_prep_fit.transform(X_train)

# Get the output feature names for the float columns. The only step that
# can change columns is the low_variance reducer.
float_output_features = X_prep_fit.named_transformers_["float_preprocess"][
    "low_variance"
].get_feature_names_out(float_columns)


# Get the output feature names for category columns (one-hot encoded)
cat_output_features = X_prep_fit.named_transformers_["cat_preprocess"][
    "one_hot_encode"
].get_feature_names_out()

# Get the output feature names for the flag columns (one-hot encoded)
flag_output_features = X_prep_fit.named_transformers_["flag_preprocess"][
    "one_hot_encode"
].get_feature_names_out()


# This is the map showing which column ranges in the output features
# correspond to which column-transformer features lists. (map from
# strings to slices)
X_prep_fit.output_indices_
