import numpy as np
from dataclasses import dataclass
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_selection import VarianceThreshold
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