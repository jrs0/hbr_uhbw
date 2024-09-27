import argparse
import importlib
from typing import Callable, Any
from sklearn.pipeline import Pipeline
from numpy.random import RandomState
from pandas import DataFrame
from pyhbr import common
from pyhbr.analysis import fit
from loguru import logger as log
from pathlib import Path

import scipy


def get_pipe_fn(model_config: dict[str, str]) -> Callable:
    """Get the pipe function based on the name in the config file

    Args:
        model_config: The dictionary in models.{model_name} in
            the config file
    """

    # Make the preprocessing/fitting pipeline
    pipe_fn_path = model_config["pipe_fn"]
    module_name, pipe_fn_name = pipe_fn_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, pipe_fn_name)


def fit_and_save(
    model_name: str,
    config: dict[str, Any],
    pipe: Pipeline,
    X_train: DataFrame,
    y_train: DataFrame,
    X_test: DataFrame,
    y_test: DataFrame,
    data_file: str,
    random_state: RandomState,
) -> None:
    """Fit the model and save the results

    Args:
        model_name: The name of the model, a key under the "models" top-level
            key in the config file
        config: The config file as a dictionary
        X_train: The features training dataframe
        y_train: The outcomes training dataframe
        X_test: The features testing dataframe
        y_test: The outcomes testing dataframe
        data_file: The name of the raw data file used for the modelling
        random_state: The source of randomness used by the model
    """

    print("Starting fit")

    # Using a larger number of bootstrap resamples will make
    # the stability analysis better, but will take longer to fit.
    num_bootstraps = config["num_bootstraps"]

    # Choose the number of bins for the calibration calculation.
    # Using more bins will resolve the risk estimates more
    # precisely, but will reduce the sample size in each bin for
    # estimating the prevalence.
    num_bins = config["num_bins"]

    # Fit the model, and also fit bootstrapped models (using resamples
    # of the training set) to assess stability.
    fit_results = fit.fit_model(
        pipe, X_train, y_train, X_test, y_test, num_bootstraps, num_bins, random_state
    )

    # Save the fitted models
    model_data = {
        "name": model_name,
        "config": config,
        "fit_results": fit_results,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "data_file": data_file,
    }

    analysis_name = config["analysis_name"]

    # If the branch is not clean, prompt the user to commit to avoid losing
    # long-running model results. Take care to only commit if the state of
    # the repository truly reflects what was run (i.e. if no changes were made
    # while the script was running).
    retry_save = True
    while retry_save:
        try:
            common.save_item(
                model_data, f"{analysis_name}_{model_name}", save_dir=config["save_dir"]
            )
            # Getting here successfully means that the save worked; exit the loop
            log.info("Saved model")
            break
        except RuntimeError as e:
            print(e)
            print("You can commit now and then retry the save after committing.")
            retry_save = common.query_yes_no(
                "Do you want to retry the save? Commit, then select yes, or choose no to exit the script."
            )


def main():

    # Keep this near the top otherwise help hangs
    parser = argparse.ArgumentParser("run-model")
    parser.add_argument(
        "-f",
        "--config-file",
        required=True,
        help="Specify the config file describing the models to fit",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Specify which model to fit. If no model is specified, all models are fitted.",
    )
    args = parser.parse_args()

    from numpy.random import RandomState
    from sklearn.model_selection import train_test_split
    import yaml

    from pyhbr.analysis import model
    from pyhbr.analysis import stability
    from pyhbr.analysis import calibration

    # Load the config file
    config = common.read_config_file(args.config_file)
    analysis_name = config["analysis_name"]
    save_dir = config["save_dir"]
    now = common.current_timestamp()

    # Set up the log file output for plot/describe script
    log_file = (
        Path(save_dir) / Path(analysis_name + f"_run_model_{now}")
    ).with_suffix(".log")
    log_format = "{time} {level} {message}"
    log_id = log.add(log_file, format=log_format)

    # Load the data files
    data, raw_data, data_path = common.load_most_recent_data_files(
        analysis_name, save_dir
    )

    # For convenience
    outcomes = data["outcomes"]

    # Base the features dataframe on the outcomes index
    features = outcomes[[]]

    # Load all features -- these are the items in the data file that
    # have a key that starts with "features_"
    for key in data.keys():
        if "features_" in key:
            log.info(f"Joining features {list(data[key].columns)} from {key} into features dataframe")
            features = features.merge(data[key], how="left", on="spell_id")

    # Check agreement between columns in features dataframe and config file
    df_list = list(features.columns)
    config_list = list(config["features"].keys())
    df_but_not_config = list(set(df_list).difference(config_list))
    config_but_not_df = list(set(config_list).difference(df_list))
    if len(df_but_not_config) != 0:
        log.warning(f"Features {df_but_not_config} are present in the features dataframe but missing from the config file")
    if len(config_but_not_df) != 0:
        log.warning(f"Features {config_but_not_df} are present in the config file but not in the features dataframe")

    # Exclude features based on config file
    columns_to_drop = []
    for column, metadata in config["features"].items():
        if "exclude" in metadata and metadata["exclude"]:
            columns_to_drop.append(column)
    log.info(f"Excluding features by exclude flag in config file: {columns_to_drop}")
    features.drop(columns=columns_to_drop, inplace=True)
    log.info(f"Remaining features: {list(features.columns)}")

    # Create a random state from a seed
    seed = config["seed"]
    log.info(f"Making random state based on config file seed {seed}")
    random_state = RandomState(seed)

    # Create the train/test split
    test_proportion = config["test_proportion"]
    log.info(f"Creating the test/train split with proportion {100*test_proportion:.1f}% in the test set")
    X_train, X_test, y_train, y_test = train_test_split(
        features, outcomes, test_size=test_proportion, random_state=random_state
    )

    # Build a list of pipes (either one if the user selected
    # a model, or all of the models present in the config file)
    if args.model is not None:
        model_name = args.model
        log.info(f"Fitting only requested model {model_name}")

        if model_name not in config["models"]:
            log.info(
                f"Error: requested model {model_name} is not present in config file {args.config}"
            )
            exit(1)

        model_config = config["models"][model_name]
        pipe_fn = get_pipe_fn(model_config)
        evaluated_config = {
            key: eval(value) for key, value in model_config["config"].items()
        }
        pipe = pipe_fn(random_state, X_train, evaluated_config)

        # Fit the model, also fit bootstrapped models (using resamples
        # of the training set) to assess stability, and save the results
        fit_and_save(
            model_name,
            config,
            pipe,
            X_train,
            y_train,
            X_test,
            y_test,
            data_path.name,
            random_state,
        )

    else:
        log.info("Fitting all models in config file")
        for model_name in config["models"]:

            model_config = config["models"][model_name]
            pipe_fn = get_pipe_fn(model_config)
            evaluated_config = {
                key: eval(value) for key, value in model_config["config"].items()
            }
            pipe = pipe_fn(random_state, X_train, evaluated_config)

            # Fit the model, also fit bootstrapped models (using resamples
            # of the training set) to assess stability, and save the results
            fit_and_save(
                model_name,
                config,
                pipe,
                X_train,
                y_train,
                X_test,
                y_test,
                data_path.name,
                random_state,
            )
