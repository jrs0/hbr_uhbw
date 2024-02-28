"""Functions for dimension-reduction of clinical codes
"""

from dataclasses import dataclass
from numpy.random import RandomState
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from pandas import DataFrame

@dataclass
class Dataset:
    """Stores either the train or test set
    """
    y: DataFrame
    X_manual: DataFrame
    X_reduce: DataFrame
    

def prepare_train_test(
    data_manual: DataFrame, data_reduce: DataFrame, random_state: RandomState
) -> (Dataset, Dataset):
    """Make the test/train datasets for manually-chosen groups and high-dimensional data

    Args:
        data_manual: The dataset with manually-chosen code groups
        data_reduce: The high-dimensional dataset
        random_state: The random state to pick the test/train split

    Returns:
        A tuple (train, test) containing the datasets to be used for training and 
            testing the models. Both contain the outcome y along with the features
            for both the manually-chosen code groups and the data for dimension 
            reduction.
    """

    # Check number of rows match
    if data_manual.shape[0] != data_reduce.shape[0]:
        raise RuntimeError(
            "The number of rows in data_manual and data_reduce do not match."
        )

    test_set_proportion = 0.25

    # First, get the outcomes (y) from the dataframe. This is the
    # source of test/train outcome data, and is used for both the
    # manual and UMAP models. Just interested in whether bleeding
    # occurred (not number of occurrences) for this experiment
    outcome_name = "bleeding_al_ani_outcome"
    y = data_manual[outcome_name]

    # Get the set of manual code predictors (X0) to use for the
    # first logistic regression model (all the columns with names
    # ending in "_before").
    X_manual = data_manual.drop(columns=[outcome_name])

    # Make a random test/train split.=
    X_train_manual, X_test_manual, y_train, y_test = train_test_split(
        X_manual, y, test_size=test_set_proportion, random_state=random_state
    )

    # Extract the test/train sets from the UMAP data based on
    # the index of the training set for the manual codes
    X_reduce = data_reduce.drop(columns=[outcome_name])
    X_train_reduce = X_reduce.loc[X_train_manual.index]
    X_test_reduce = X_reduce.loc[X_test_manual.index]

    # Store the test/train data together
    train = Dataset(y_train, X_train_manual, X_train_reduce)
    test = Dataset(y_test, X_test_manual, X_test_reduce)
    
    return train, test

def make_reducer_pipeline(reducer, cols_to_reduce: list[str]) -> Pipeline:
    """Make a wrapper that applies dimension reduction to a subset of columns.

    A column transformer is necessary if only some of the columns should be
    dimension-reduced, and others should be preserved. The resulting pipeline
    is intended for use in a scikit-learn pipeline taking a pandas DataFrame as
    input (where a subset of the columns are cols_to_reduce).

    Args:
        reducer: The dimension reduction model to use for reduction
        cols_to_reduce: The list of column names to reduce

    Returns:
        A pipeline which contains the column_transformer that applies the
            reducer to cols_to_reduce. This can be included as a step in a
            larger pipeline.
    """
    column_transformer = ColumnTransformer(
        [("reducer", reducer, cols_to_reduce)],
        remainder="passthrough",
        verbose_feature_names_out=True,
    )
    return Pipeline([("column_transformer", column_transformer)])

def make_full_pipeline(model: Pipeline, reducer: Pipeline = None) -> Pipeline:
    """Make a model pipeline from the model part and dimension reduction

    This pipeline has one or two steps:
    
    * If no reduction is performed, the only step is "model"
    * If dimension reduction is performed, the steps are "reducer", "model"

    This function can be used to make the pipeline with no dimension
    (pass None to reducer). Otherwise, pass the reducer which will reduce
    a subset of the columns before fitting the model (use make_column_transformer
    to create this argument).

    Args:
        model: A list of model fitting steps that should be applied
            after the (optional) dimension reduction.
        reducer: If non-None, this reduction pipeline is applied before
            the model to reduce a subset of the columns.

    Returns:
        A scikit-learn pipeline that can be fitted to training data.
    """
    if reducer is not None:
        return Pipeline([("reducer", reducer), ("model", model)])
    else:
        return Pipeline([("model", model)])
    
