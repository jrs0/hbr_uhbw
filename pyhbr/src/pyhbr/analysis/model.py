import numpy as np
from dataclasses import dataclass
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_selection import VarianceThreshold
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from pandas import DataFrame


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


def make_category_preprocessor(X_train: DataFrame) -> Preprocessor | None:
    """Create a preprocessor for string/category columns

    Columns in the training features that are discrete, represented
    using strings ("object") or "category" dtypes, should be one-hot
    encoded. This generates one new columns for each possible value
    in the original columns.

    The ColumnTransformer transformer created from this preprocessor
    will be called "category".

    Args:
        X_train: The training features

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
                    handle_unknown="infrequent_if_exist", min_frequency=0.002
                ),
            ),
        ]
    )

    return Preprocessor("category", pipe, columns)


def make_flag_preprocessor(X_train: DataFrame) -> Preprocessor | None:
    """Create a preprocessor for flag columns

    Columns in the training features that are flags (bool + NaN) are
    represented using Int8 (because bool does not allow NaN). These
    columns are also one-hot encoded.
    
    The ColumnTransformer transformer created from this preprocessor
    will be called "flag".
    
    Args:
        X_train: The training features

    Returns:
        A preprocessor for processing the flag columns. None is
            returned if the training features do not contain any
            Int8 columns.
    """

    # Flag columns (encoded using Int8, which supports NaN), should be one-hot
    # encoded (considered separately from category in case I want to do something
    # different with these).
    columns = X_train.columns[(X_train.dtypes == "Int8")]
    
    # Return None if there are no discrete columns.
    if len(columns) == 0:
        return None
    
    pipe = Pipeline(
        [
            (
                "one_hot_encode",
                OneHotEncoder(handle_unknown="infrequent_if_exist"),
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


def get_preprocessed_column_map(
    fit: Pipeline, preprocessors: list[Preprocessor | None]
) -> dict[str, str]:
    """_summary_

    Args:
        fit: A fitted sklearn pipeline, containing a "preprocess"
            step.
        preprocessors:

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

    # Remove None values from the list (occurs when no columns
    # of that type are present in the training data)
    not_none = [pre for pre in preprocessors if pre is not None]

    for pre in not_none:
        name = pre.name
        step_name = relevant_step[name]

        # Get the step which transforms column names
        step = preprocess.named_transformers_[pre.name][step_name]

        # A special case is required for the low_variance columns
        # which need original list of columns passing in
        if name == "float":
            columns = step.get_feature_names_out(pre.columns)
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
    prep_columns = get_preprocessed_column_map(fit, preprocessors)
    X_numpy = preprocess.transform(X)

    # Convert the numpy array or sparse array to a dataframe
    if scipy.sparse.issparse(X_train_numpy):
        return DataFrame.sparse.from_spmatrix(
            X_numpy,
            columns=prep_columns["column"],
            index=X_train.index,
        )
    else:
        return DataFrame(
            X_numpy,
            columns=prep_columns["column"],
            index=X_train.index,
        )