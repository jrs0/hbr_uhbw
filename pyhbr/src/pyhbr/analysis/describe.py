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
