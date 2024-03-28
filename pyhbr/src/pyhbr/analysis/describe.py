from pandas import Series, DataFrame


def proportion_nonzero(column: Series) -> float:
    """Get the proportion of non-zero values in a column"""
    return (column > 0).sum() / len(column)


def get_column_rates(data: DataFrame) -> Series:
    """Get the proportion of rows in each column that are non-zero

    Either pass the full table, or subset it based
    on a condition to get the rates for that subset.

    Args:
        data: A table containing columns where the proportion
            of non-zero rows should be calculated.

    Returns:
        A Series (single column) with one row per column in the
            original data, containing the rate of non-zero items
            in each column. The Series is indexed by the names of
            the columns, with "_rate" appended.
    """
    return Series(
        {name + "_rate": proportion_nonzero(col) for name, col in data.items()}
    ).sort_values()

def proportion_missingness(data: DataFrame) -> Series:
    """Get the proportion of missing values in each column
    
    Args:
        data: A table where missingness should be calculate
            for each column

    Returns:
        The proportion of missing values in each column, indexed
            by the original table column name. The values are sorted
            in order of increasing missingness
    """
    return (data.isna().sum() / len(data)).sort_values().rename("missingness")

def zero_variance_columns(data: DataFrame) -> Series:
    """Check which columns of the input table have zero variance
    
    Zero variance is defined as either having all missing values,
    or having only one value after excluding missing values.
    
    Args:
        data: The table to check for zero variance

    Returns:
        A Series containing bool, indexed by the column name
            in the original data, containing whether the column
            has zero variance.
    """
    return data.apply(lambda col: len(col.value_counts()) < 2).rename("zero_variance")