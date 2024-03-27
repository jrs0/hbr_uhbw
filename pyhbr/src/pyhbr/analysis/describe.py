from pandas import Series

def proportion_nonzero(column: Series) -> float:
    """Get the proportion of non-zero values in a column
    """
    return (column > 0).sum() / len(column)