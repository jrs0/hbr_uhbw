import argparse

# Keep this near the top otherwise help hangs
parser = argparse.ArgumentParser("icb_basic_model")
parser.add_argument(
    "-f",
    "--config-file",
    required=True,
    help="Specify the config file describing the models to fit",
)
parser.add_argument(
    "-m",
    "--model",
    required=True,
    help="Specify which model to fit",
)
args = parser.parse_args()

import importlib
from numpy.random import RandomState
from sklearn.model_selection import train_test_split
import yaml

from pyhbr.analysis import model
from pyhbr.analysis import fit
from pyhbr.analysis import stability
from pyhbr.analysis import calibration
from pyhbr import common

# importlib.reload(model)
# importlib.reload(calibration)
# importlib.reload(common)
# importlib.reload(stability)
# importlib.reload(fit)

# Read the configuration file
with open(args.config_file) as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(f"Failed to load config file: {exc}")
        exit(1)

# Load outcome and training data
icb_basic_data = common.load_item("icb_basic_data", save_dir=config["save_dir"])

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
seed = config["seed"]
random_state = RandomState(seed)

# Create the train/test split
test_proportion = config["test_proportion"]
X_train, X_test, y_train, y_test = train_test_split(
    features, outcomes, test_size=test_proportion, random_state=random_state
)

# Using a larger number of bootstrap resamples will make
# the stability analysis better, but will take longer to fit.
num_bootstraps = config["num_bootstraps"]

# Choose the number of bins for the calibration calculation.
# Using more bins will resolve the risk estimates more
# precisely, but will reduce the sample size in each bin for
# estimating the prevalence.
num_bins = config["num_bins"]

model_name = args.model
if model_name not in config["models"]:
    print(
        f"Error: requested model {model_name} is not present in config file {args.config}"
    )
    exit(1)

model_config = config["models"][model_name]

# Make the preprocessing/fitting pipeline
pipe_fn_path = model_config["pipe_fn"]
module_name, pipe_fn_name = pipe_fn_path.rsplit(".", 1)
module = importlib.import_module(module_name)
pipe_fn = getattr(module, pipe_fn_name)

pipe = pipe_fn(random_state, X_train)

# Fit the model, and also fit bootstrapped models (using resamples
# of the training set) to assess stability.
fit_results = fit.fit_model(
    pipe, X_train, y_train, X_test, y_test, num_bootstraps, num_bins, random_state
)

# Process the dataset
# model.get_features(
#     fit_results["fitted_models"]["bleeding"].M0, X_train
# ).mean().sort_values()

# Plot a tree from the forest
# fig, ax = plt.subplots(1)
# model.plot_random_forest(ax, fit_results, "bleeding", 3)
# plt.show()

# Save the fitted models
model_data = {
    "config": config,
    "fit_results": fit_results,
    "X_train": X_train,
    "X_test": X_test,
    "y_train": y_train,
    "y_test": y_test,
    "icb_basic_data": icb_basic_data,
}
common.save_item(model_data, f"icb_basic_{model_name}", save_dir=config["save_dir"])
