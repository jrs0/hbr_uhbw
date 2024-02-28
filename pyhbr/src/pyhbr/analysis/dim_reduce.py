"""Functions for dimension-reduction of clinical codes
"""

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

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
    
