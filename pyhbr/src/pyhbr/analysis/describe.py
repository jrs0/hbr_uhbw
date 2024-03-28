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

def nearly_constant(data: DataFrame, threshold: float) -> Series:
    """Check which columns of the input table have low variation
    
    A column is considered low variance if the proportion of rows
    containing NA or the most common non-NA value exceeds threshold.
    For example, if NA and one other value together comprise 99% of
    the column, then it is considered to be low variance based on
    a threshold of 0.9.
    
    Args:
        data: The table to check for zero variance
        threshold: The proportion of the column that must be NA or
            the most common value above which the column is considered
            low variance.

    Returns:
        A Series containing bool, indexed by the column name
            in the original data, containing whether the column
            has low variance.
    """
    
    def low_variance(column: Series) -> bool:
        
        if len(column) == 0:
            # If the column has length zero, consider
            # it low variance
            return True
        
        if len(column.dropna()) == 0:
            # If the column is all-NA, it is low variance
            # independently of the threshold
            return True
        
        # Else, if the proportion of NA and the most common
        # non-NA value is higher than threshold, the column 
        # is low variance
        na_count = column.isna().sum()
        counts = column.value_counts()
        most_common_value_count = counts.iloc[0]
        if (na_count + most_common_value_count) / len(column) > threshold:
            return True
        
        return False
    
    return data.apply(low_variance).rename("nearly_constant")