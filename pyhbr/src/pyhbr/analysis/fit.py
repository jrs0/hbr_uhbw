from numpy.random import RandomState
from pandas import DataFrame
from sklearn.pipeline import Pipeline
from pyhbr.analysis import stability, calibration, roc, model
from sklearn.inspection import permutation_importance
from loguru import logger as log

def fit_model(
    pipe: Pipeline,
    X_train: DataFrame,
    y_train: DataFrame,
    X_test: DataFrame,
    y_test: DataFrame,
    num_bootstraps: int,
    num_bins: int,
    random_state: RandomState,
) -> dict[str, DataFrame | Pipeline]:
    """Fit the model and bootstrap models, and calculate model performance

    Args:
        pipe: The model pipeline to fit
        X_train: Training features
        y_train: Training outcomes (containing "bleeding"/"ischaemia" columns)
        X_test: Test features
        y_test: Test outcomes
        num_bootstraps: The number of resamples of the training set to use to
            fit bootstrap models.
        num_bins: The number of equal-size bins to split risk estimates into
            to calculate calibration curves.
        random_state: The source of randomness for the resampling and fitting
            process.

    Returns:
        Dictionary with keys "probs", "calibrations", "roc_curves", "roc_aucs".
    """

    # Calculate the results of the model
    probs = {}
    calibrations = {}
    roc_curves = {}
    roc_aucs = {}
    fitted_models = {}
    feature_importances = {}
    for outcome in ["bleeding", "ischaemia"]:

        log.info(f"Fitting {outcome} model")

        # Fit the bleeding and ischaemia models on the training set
        # and bootstrap resamples of the training set (to assess stability)
        fitted_models[outcome] = stability.fit_model(
            pipe, X_train, y_train.loc[:, outcome], num_bootstraps, random_state
        )

        log.info(f"Running permutation feature importance on {outcome} model M0")
        M0 = fitted_models[outcome].M0
        r = permutation_importance(
            M0,
            X_test,
            y_test.loc[:, outcome],
            n_repeats=20,
            random_state=random_state,
            scoring="roc_auc",
        )
        feature_importances[outcome] = {
            "names": X_train.columns,
            "result": r,
        }

        # Get the predicted probabilities associated with all the resamples of
        # the bleeding and ischaemia models
        probs[outcome] = stability.predict_probabilities(fitted_models[outcome], X_test)

        # Get the calibration of the models
        calibrations[outcome] = calibration.get_variable_width_calibration(
            probs[outcome], y_test.loc[:, outcome], num_bins
        )

        # Calculate the ROC curves for the models
        roc_curves[outcome] = roc.get_roc_curves(probs[outcome], y_test.loc[:, outcome])
        roc_aucs[outcome] = roc.get_auc(probs[outcome], y_test.loc[:, outcome])

    return {
        "probs": probs,
        "calibrations": calibrations,
        "roc_aucs": roc_aucs,
        "roc_curves": roc_curves,
        "fitted_models": fitted_models,
        "feature_importances": feature_importances,
    }
