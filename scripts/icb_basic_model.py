import importlib

from numpy.random import RandomState
from sklearn.model_selection import train_test_split

from pyhbr.analysis import model
from pyhbr.analysis import fit
from pyhbr.analysis import stability
from pyhbr.analysis import calibration
from pyhbr import common

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

# Create a random state from a seed
seed = 0
random_state = RandomState(seed)

# Create the train/test split
test_proportion = 0.25
X_train, X_test, y_train, y_test = train_test_split(
    features, outcomes, test_size=test_proportion, random_state=random_state
)

# Using a larger number of bootstrap resamples will make
# the stability analysis better, but will take longer to fit.
num_bootstraps = 10

# Choose the number of bins for the calibration calculation.
# Using more bins will resolve the risk estimates more
# precisely, but will reduce the sample size in each bin for
# estimating the prevalence.
num_bins = 5

# Make the preprocessing/fitting pipeline
pipes = {
    "random_forest": model.make_random_forest(random_state, X_train),
    "logistic_regression": model.make_logistic_regression(random_state, X_train),
    "xgboost": model.make_xgboost(random_state, X_train),
}

# Fit the model, and also fit bootstrapped models (using resamples
# of the training set) to assess stability.
fit_results = {
    model_name: fit.fit_model(
        pipe, X_train, y_train, X_test, y_test, num_bootstraps, num_bins, random_state
    )
    for model_name, pipe in pipes.items()
}

# Process the dataset
model.get_features(
    fit_results["fitted_models"]["bleeding"].M0, X_train
).mean().sort_values()

# Plot a tree from the forest
fig, ax = plt.subplots(1)
model.plot_random_forest(ax, fit_results, "bleeding", 3)
plt.show()

# Save the fitted models
icb_basic_models = {
    "seed": seed,
    "test_proportion": test_proportion,
    "num_bins": num_bins,
    "num_bootstraps": num_bootstraps,
    "fit_results": fit_results,
    "X_train": X_train,
    "X_test": X_test,
    "y_train": y_train,
    "y_test": y_test,
    "icb_basic_data": icb_basic_data    
}
common.save_item(icb_basic_models, "icb_basic_models")

