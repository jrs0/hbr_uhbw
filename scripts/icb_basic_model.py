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

import matplotlib.pyplot as plt

importlib.reload(model)
importlib.reload(calibration)


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

# This is an sqlalchemy problem -- some column names are
# sqlalchemy.sql.elements.quoted_name, which is nearly impossible
# to discover (because dtype is object and it prints as a string)
# Fix this upstream.
features.columns = [str(col) for col in features.columns]

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

# Select the outcome for modelling
outcome_name = "bleeding_outcome"

# Create a model to be trained on the preprocessed training set
mod = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state)

pipe = Pipeline([("preprocess", preprocess), ("model", mod)])

# Fit the bleeding and ischaemia models on the training set
# and bootstrap resamples of the training set (to assess stability)
fitted_bleeding_model = stability.fit_model(
    pipe, X_train, y_train.loc[:, "bleeding_outcome"], 50, random_state
)
fitted_ischaemia_model = stability.fit_model(
    pipe, X_train, y_train.loc[:, "ischaemia_outcome"], 50, random_state
)

# Get the predicted probabilities associated with all the resamples of
# the bleeding and ischaemia models
bleeding_probs = stability.predict_probabilities(fitted_bleeding_model, X_test)
ischaemia_probs = stability.predict_probabilities(fitted_ischaemia_model, X_test)

# Plot the stability of predicted probabilities
fig, ax = plt.subplots(1,2)
stability.plot_instability(ax[0], bleeding_probs, y_test.loc[:,"bleeding_outcome"], "Stability of Predicted Risks of Bleeding")
stability.plot_instability(ax[1], ischaemia_probs, y_test.loc[:,"ischaemia_outcome"], "Stability of Predicted Risks of Ischaemia")
plt.show()

# Calculate the ROC curves for the models
bleeding_roc_curves = roc.get_roc_curves(bleeding_probs, y_test.loc[:, "bleeding_outcome"])
ischaemia_roc_curves = roc.get_roc_curves(ischaemia_probs, y_test.loc[:, "ischaemia_outcome"])
bleeding_auc = roc.get_auc(bleeding_probs, y_test.loc[:, "bleeding_outcome"])
ischaemia_auc = roc.get_auc(ischaemia_probs, y_test.loc[:, "ischaemia_outcome"])

# Plot the ROC curves for the models
fig, ax = plt.subplots(1,2)
roc.plot_roc_curves(ax[0], bleeding_roc_curves, bleeding_auc, "Bleeding ROC Curves")
roc.plot_roc_curves(ax[1], ischaemia_roc_curves, ischaemia_auc, "Ischaemia ROC Curves")
plt.show()

# Get the calibration of the models
bleeding_calibration_curves = calibration.get_calibration(bleeding_probs, y_test.loc[:, "bleeding_outcome"], 15)
ischaemia_calibration_curves = calibration.get_calibration(ischaemia_probs, y_test.loc[:, "ischaemia_outcome"], 15)

# Plot the calibration curves
fig, ax = plt.subplots(1,1)
calibration.plot_calibration_curves(ax, bleeding_calibration_curves, "red", "testtt")
calibration.plot_calibration_curves(ax, ischaemia_calibration_curves, "blue", "test")
plt.show()

# View the features that go directly into the model. This dataframe
# has the column that the model sees (after the preprocessing steps).
F_train = model.get_features(fit, X_train)

probs = fit.predict_proba(X_test)

auc = roc_auc_score(y_test.loc[:, outcome_name], probs[:, 1])
auc


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
