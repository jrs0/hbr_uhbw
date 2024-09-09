from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.random import RandomState
from pandas import DataFrame, Series
import pandas as pd

from sklearn.base import TransformerMixin, ClassifierMixin, BaseEstimator
from sklearn.pipeline import Pipeline
from sklearn.utils.multiclass import unique_labels
from sklearn.preprocessing import OneHotEncoder, StandardScaler, MinMaxScaler
from sklearn.feature_selection import VarianceThreshold
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import ComplementNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import RandomizedSearchCV
from sklearn import tree

from xgboost import XGBClassifier

from matplotlib.axes import Axes

import scipy

def trade_off_model_bleeding_risk(features: DataFrame) -> Series:
    """ARC-HBR bleeding part of the trade-off model

    This function implements the bleeding model contained here
    https://pubmed.ncbi.nlm.nih.gov/33404627/. The numbers used
    below come from correspondence with the authors.


    Args:
        features: must contain age, smoking, copd, hb, egfr_x, oac.

    Returns:
        The bleeding risks as a Series.
    """

    # Age component, right=False for >= 65, setting upper limit == 1000 to catch all
    age = pd.cut(features["age"], [0, 65, 1000], labels=[1, 1.5], right=False).astype("float")

    smoking = np.where(features["smoking"] == "yes", 1.47, 1)
    copd = np.where(features["copd"].fillna(0) == 1, 1.39, 1)

    # Fill NA with a high Hb value (50) to treat missing as low risk
    hb = pd.cut(
        10 * features["hb"].fillna(50),
        [0, 110, 130, 1000],
        labels=[3.99, 1.69, 1],
        right=False,
    ).astype("float")

    # Fill NA with a high eGFR value (500) to treat missing as low risk
    egfr = pd.cut(
        features["egfr_x"].fillna(500),
        [0, 30, 60, 1000],
        labels=[1.43, 0.99, 1],
        right=False,
    ).astype("float")

    # TODO complex and liver cancer surgery
    complex_score = 1.0
    liver_cancer_surgery = 1.0

    oac = np.where(features["oac"] == 1, 2.0, 1.0)

    # Calculate bleeding risk
    xb = age*smoking*copd*liver_cancer_surgery*hb*egfr*complex_score*oac
    risk = 1 - 0.986**xb
    
    return risk

def trade_off_model_ischaemia_risk(features: DataFrame) -> Series:
    """ARC-HBR ischaemia part of the trade-off model

    This function implements the bleeding model contained here
    https://pubmed.ncbi.nlm.nih.gov/33404627/. The numbers used
    below come from correspondence with the authors.

    Args:
        features: must contain diabetes_before, smoking, 

    Returns:
        The ischaemia risks as a Series.
    """

    diabetes = np.where(features["diabetes_before"] > 0, 1.56, 1)
    smoking = np.where(features["smoking"] == "yes", 1.47, 1)
    prior_mi = np.where(features["mi_schnier_before"] > 0, 1.89, 1)
    
    # Interpreting "presentation" as stemi vs. nstemi
    presentation = np.where(features["stemi_index"], 1.82, 1)

    # Fill NA with a high Hb value (50) to treat missing as low risk
    hb = pd.cut(
        10 * features["hb"].fillna(50),
        [0, 110, 130, 1000],
        labels=[1.5, 1.27, 1],
        right=False,
    ).astype("float")

    # Fill NA with a high eGFR value (500) to treat missing as low risk
    egfr = pd.cut(
        features["egfr_x"].fillna(500),
        [0, 30, 60, 1000],
        labels=[1.69, 1.3, 1],
        right=False,
    ).astype("float")

    # TODO complex and bare metal stent (missing from data)
    complex_score = 1.0
    bms = 1.0

    # Calculate bleeding risk
    xb = diabetes*smoking*prior_mi*presentation*hb*egfr*complex_score*bms
    risk = 1 - 0.986**xb
    
    return risk

class TradeOffModel(ClassifierMixin, BaseEstimator):
    
    def fit(self, X, y):
        """Use the name of the Y variable to choose between
        bleeding and ischaemia
        """
        
        self.classes_ = unique_labels(y)
        
        self.X_ = X
        self.y_ = y

        # Return the classifier

        return self

    def decision_function(self, X: DataFrame) -> DataFrame:
        return self.predict_proba(X)[:, 1]

    def predict_proba(self, X: DataFrame) -> DataFrame:
        risk = trade_off_model_bleeding_risk(X)
        return np.column_stack((1-risk, risk))
    
    # def predict(self, X: DataFrame) -> DataFrame:
    #     risk = predict_proba(X)[:, 1]
    #     return risk > 0.01

class DenseTransformer(TransformerMixin):
    """Useful when the model requires a dense matrix
    but the preprocessing steps produce a sparse output
    """

    def fit(self, X, y=None, **fit_params):
        return self

    def transform(self, X, y=None, **fit_params):
        if hasattr(X, "todense"):
            return np.asarray(X.todense())
        else:
            return X
        

@dataclass
class Preprocessor:
    """Preprocessing steps for a subset of columns

    This holds the set of preprocessing steps that should
    be applied to a subset of the (named) columns in the
    input training dataframe.

    Multiple instances of this classes (for different subsets
    of columns) are grouped together to create a ColumnTransformer,
    which preprocesses all columns in the training dataframe.

    Args:
        name: The name of the preprocessor (which will become
            the name of the transformer in ColumnTransformer
        pipe: The sklearn Pipeline that should be applied to
            the set of columns
        columns: The set of columns that should have pipe
            applied to them.
    """

    name: str
    pipe: Pipeline
    columns: list[str]


def make_category_preprocessor(X_train: DataFrame, drop=None) -> Preprocessor | None:
    """Create a preprocessor for string/category columns

    Columns in the training features that are discrete, represented
    using strings ("object") or "category" dtypes, should be one-hot
    encoded. This generates one new columns for each possible value
    in the original columns.

    The ColumnTransformer transformer created from this preprocessor
    will be called "category".

    Args:
        X_train: The training features
        drop: The drop argument to be passed to OneHotEncoder. Default
            None means no features will be dropped. Using "first" drops
            the first item in the category, which is useful to avoid
            collinearity in linear models.

    Returns:
        A preprocessor for processing the discrete columns. None is
            returned if the training features do not contain any
            string/category columns
    """

    # Category columns should be one-hot encoded (in all these one-hot encoders,
    # consider the effect of linear dependence among the columns due to the extra
    # variable compared to dummy encoding -- the relevant parameter is called
    # 'drop').
    columns = X_train.columns[
        (X_train.dtypes == "object") | (X_train.dtypes == "category")
    ]

    # Return None if there are no discrete columns.
    if len(columns) == 0:
        return None

    pipe = Pipeline(
        [
            (
                "one_hot_encoder",
                OneHotEncoder(
                    handle_unknown="infrequent_if_exist", min_frequency=0.002, drop=drop
                ),
            ),
        ]
    )

    return Preprocessor("category", pipe, columns)


def make_flag_preprocessor(X_train: DataFrame, drop=None) -> Preprocessor | None:
    """Create a preprocessor for flag columns

    Columns in the training features that are flags (bool + NaN) are
    represented using Int8 (because bool does not allow NaN). These
    columns are also one-hot encoded.

    The ColumnTransformer transformer created from this preprocessor
    will be called "flag".

    Args:
        X_train: The training features.
        drop: The drop argument to be passed to OneHotEncoder. Default
            None means no features will be dropped. Using "first" drops
            the first item in the category, which is useful to avoid
            collinearity in linear models.

    Returns:
        A preprocessor for processing the flag columns. None is
            returned if the training features do not contain any
            Int8 columns.
    """

    # Flag columns (encoded using Int8, which supports NaN), should be one-hot
    # encoded (considered separately from category in case we want to do something
    # different with these).
    columns = X_train.columns[(X_train.dtypes == "Int8")]

    # Return None if there are no discrete columns.
    if len(columns) == 0:
        return None

    pipe = Pipeline(
        [
            (
                "one_hot_encode",
                OneHotEncoder(handle_unknown="infrequent_if_exist", drop=drop),
            ),
        ]
    )

    return Preprocessor("flag", pipe, columns)


def make_float_preprocessor(X_train: DataFrame) -> Preprocessor | None:
    """Create a preprocessor for float (numerical) columns

    Columns in the training features that are numerical are encoded
    using float (to distinguish them from Int8, which is used for
    flags).

    Missing values in these columns are imputed using the mean, then
    low variance columns are removed. The remaining columns are
    centered and scaled.

    The ColumnTransformer transformer created from this preprocessor
    will be called "float".

    Args:
        X_train: The training features

    Returns:
        A preprocessor for processing the float columns. None is
            returned if the training features do not contain any
            Int8 columns.
    """

    # Numerical columns -- impute missing values, remove low variance
    # columns, and then centre and scale the rest.
    columns = X_train.columns[(X_train.dtypes == "float")]

    # Return None if there are no discrete columns.
    if len(columns) == 0:
        return None

    pipe = Pipeline(
        [
            ("impute", SimpleImputer(missing_values=np.nan, strategy="mean")),
            ("low_variance", VarianceThreshold()),
            ("scaler", StandardScaler()),
        ]
    )

    return Preprocessor("float", pipe, columns)


def make_columns_transformer(
    preprocessors: list[Preprocessor | None],
) -> ColumnTransformer:

    # Remove None values from the list (occurs when no columns
    # of that type are present in the training data)
    not_none = [pre for pre in preprocessors if pre is not None]

    # Make the list of tuples in the format for ColumnTransformer
    tuples = [(pre.name, pre.pipe, pre.columns) for pre in not_none]

    return ColumnTransformer(tuples, remainder="drop")


def get_num_feature_columns(fit: Pipeline) -> int:
    """Get the total number of feature columns
    Args:
        fit: The fitted pipeline, containing a "preprocess"
            step.

    Returns:
        The total number of columns in the features, after
            preprocessing.
    """

    # Get the map from column transformers to the slices
    # that they occupy in the training data
    preprocess = fit["preprocess"]
    column_slices = preprocess.output_indices_

    total = 0
    for s in column_slices.values():
        total += s.stop - s.start

    return total

def get_feature_importances(fit: Pipeline) -> DataFrame:
    """Get a table of the features used in the model along with feature importances

    Args:
        fit: The fitted Pipeline
        
    Returns:
        Contains a column for feature names, a column for type, and a feature importance column.
    """
    
    df = get_feature_names(fit)
    
    model = fit["model"]
    
    # Check if the Pipe is a raw model, or a CV search (either
    # grid or randomised)
    if hasattr(model, "best_estimator_"):
        # CV model
        importances = model.best_estimator_.feature_importances_
    else:
        importances = model.feature_importances_
        
    df["feature_importances"] = importances
    return df.sort_values("feature_importances", ascending=False)
        

def get_feature_names(fit: Pipeline) -> DataFrame:
    """Get a table of feature names

    The feature names are the names of the columns in the output
    from the preprocessing step in the fitted pipeline

    Args:
        fit: A fitted sklearn pipeline, containing a "preprocess"
            step.

    Raises:
        RuntimeError: _description_

    Returns:
        dict[str, str]: _description_
    """

    # Get the fitted ColumnTransformer from the fitted pipeline
    preprocess = fit["preprocess"]

    # Map from preprocess name to the relevant step that changes
    # column names. This must be kept consistent with the
    # make_*_preprocessor functions
    relevant_step = {
        "category": "one_hot_encoder",
        "float": "low_variance",
        "flag": "one_hot_encode",
    }

    # Get the map showing which column transformers (preprocessors)
    # are responsible which which slices of columns in the output
    # training dataframe
    column_slices = preprocess.output_indices_

    # Make an empty list of the right length to store all the columns
    column_names = get_num_feature_columns(fit) * [None]

    # Make an empty list for the preprocessor groups
    prep_names = get_num_feature_columns(fit) * [None]

    for name, pipe, columns in preprocess.transformers_:

        # Ignore the remainder step
        if name == "remainder":
            continue

        step_name = relevant_step[name]

        # Get the step which transforms column names
        step = pipe[step_name]

        # A special case is required for the low_variance columns
        # which need original list of columns passing in
        if name == "float":
            columns = step.get_feature_names_out(columns)
        else:
            columns = step.get_feature_names_out()

        # Get the properties of the slice where this set of
        # columns sits
        start = column_slices[name].start
        stop = column_slices[name].stop
        length = stop - start

        # Check the length of the slice matches the output
        # columns length
        if len(columns) != length:
            raise RuntimeError(
                "Length of output columns slice did not match the length of the column names list"
            )

        # Get the current slice corresponding to this preprocess
        s = column_slices[name]

        # Insert the list of colum names by slice
        column_names[s] = columns

        # Store the preprocessor name for the columns
        prep_names[s] = (s.stop - s.start) * [name]

    return DataFrame({"column": column_names, "preprocessor": prep_names})


def get_features(fit: Pipeline, X: DataFrame) -> DataFrame:
    """Get the features after preprocessing the input X dataset

    The features are generated by the "preprocess" step in the fitted
    pipe. This step is a column transformer that one-hot-encodes
    discrete data, and imputes, centers, and scales numerical data.

    Note that the result may be a dense or sparse Pandas dataframe,
    depending on whether the preprocessing steps produce a sparse
    numpy array or not.

    Args:
        fit: Fitted pipeline with "preprocess" step.
        X: An input dataset (either training or test) containing
            the input columns to be preprocessed.

    Returns:
        The resulting feature columns generated by the preprocessing
            step.
    """

    # Get the preprocessing step and new feature column names
    preprocess = fit["preprocess"]
    prep_columns = get_feature_names(fit)
    X_numpy = preprocess.transform(X)

    # Convert the numpy array or sparse array to a dataframe
    if scipy.sparse.issparse(X_numpy):
        return DataFrame.sparse.from_spmatrix(
            X_numpy,
            columns=prep_columns["column"],
            index=X.index,
        )
    else:
        return DataFrame(
            X_numpy,
            columns=prep_columns["column"],
            index=X.index,
        )

def make_trade_off(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:
    """Make the ARC HBR bleeding/ischaemia trade-off model

    Args:
        random_state: Source of randomness for creating the model
        X_train: The training dataset containing all features for modelling

    Returns:
        The preprocessing and fitting pipeline.
    """

    #preprocess = make_columns_transformer(preprocessors)
    mod = TradeOffModel()
    return Pipeline([("model", mod)])

def make_random_forest(random_state: RandomState, X_train: DataFrame) -> Pipeline:
    """Make the random forest model

    Args:
        random_state: Source of randomness for creating the model
        X_train: The training dataset containing all features for modelling

    Returns:
        The preprocessing and fitting pipeline.
    """

    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    mod = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=random_state
    )
    return Pipeline([("preprocess", preprocess), ("model", mod)])

def make_random_forest_cv(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:
    """Random forest model trained using cross validation

    Args:
        random_state: Source of randomness for creating the model
        X_train: The training dataset containing all features for modelling
        config: The dictionary of keyword arguments to configure the CV search.

    Returns:
        The preprocessing and fitting pipeline.
    """
    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)

    mod = RandomizedSearchCV(
        RandomForestClassifier(random_state=random_state),
        param_distributions=config,
        random_state=random_state,
        scoring="roc_auc",
        cv=2,
        verbose=3
    )
    return Pipeline([("preprocess", preprocess), ("model", mod)])
    

def make_nearest_neighbours_cv(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:
    """Nearest neighbours classifier trained using cross validation

    Args:
        random_state: Source of randomness for creating the model
        X_train: The training dataset containing all features for modelling
        config: The dictionary of keyword arguments to configure the CV search.

    Returns:
        The preprocessing and fitting pipeline.
    """
    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)

    mod = RandomizedSearchCV(
        KNeighborsClassifier(),
        param_distributions=config,
        random_state=random_state,
        scoring="roc_auc",
        cv=2,
        verbose=3
    )
    return Pipeline([("preprocess", preprocess), ("model", mod)])

def plot_random_forest(ax: Axes, fit_results: Pipeline, outcome: str, tree_num: int):

    # Get the primary model for the outcome
    fitted_pipe = fit_results["fitted_models"][outcome].M0

    first_tree = fitted_pipe["model"].estimators_[tree_num]
    names = get_feature_names(fitted_pipe)["column"]

    tree.plot_tree(
        first_tree,
        feature_names=names,
        class_names=[outcome, "no_" + outcome],
        filled=True,
        ax=ax,
        fontsize=5
    )

def make_logistic_regression(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]):
    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    mod = LogisticRegression(random_state=random_state, **config)
    return Pipeline([("preprocess", preprocess), ("model", mod)])


def make_xgboost(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:

    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    mod = XGBClassifier(tree_method="hist")
    return Pipeline([("preprocess", preprocess), ("model", mod)])

def make_svm(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:

    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    mod = SVC(probability=True, verbose=3)
    return Pipeline([("preprocess", preprocess), ("model", mod)])

def make_mlp(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:

    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    mod = MLPClassifier(verbose=3, **config, random_state=random_state)
    return Pipeline([("preprocess", preprocess), ("model", mod)])

def make_cnb(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:

    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    
    mod = ComplementNB(**config)
    return Pipeline([
        ("preprocess", preprocess),
        ("to_dense", DenseTransformer()), # Required because MinMaxScaler requires dense
        ("make_positive", MinMaxScaler()), # Required to make features positive
        ("model", mod)
    ])
    
def make_abc(random_state: RandomState, X_train: DataFrame, config: dict[str, Any]) -> Pipeline:
    """Make the AdaBoost classifier pipeline
    """

    preprocessors = [
        make_category_preprocessor(X_train),
        make_flag_preprocessor(X_train),
        make_float_preprocessor(X_train),
    ]
    preprocess = make_columns_transformer(preprocessors)
    mod = AdaBoostClassifier(**config, random_state=random_state)
    return Pipeline([("preprocess", preprocess), ("model", mod)])