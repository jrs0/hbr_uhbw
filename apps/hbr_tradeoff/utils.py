"""Utilities for input/output in streamlit apps
"""

from pandas import DataFrame

def dict_to_dataframe(x: dict[str, float]) -> DataFrame:
    """Convert the dictionary format of probabilities to DataFrame
    
    Two formats are used for non-independent probabilities of bleeding
    and ischaemia in the apps:
    
    * A dictionary, with keys "ni_nb" (no ischaemia and no bleed),
        "ni_b" (no ischaemia and bleed), and "i_nb" (ischaemia and no bleed).
    * A dataframe with columns "No Bleed" and "Bleed", and index "No Ischaemia"
        and "Ischaemia".
        
    Note that the dictionary only contains 3 values -- the fourth is calculated
    assuming all elements sum to 1.0.

    Raises:
        KeyError if the input dictionary is missing keys

    Args:
        x: A dictionary of probabilities with three keys "ni_nb", "ni_b", and
            "i_nb".

    Returns:
        A DataFrame with columns "No Bleed", "Bleed" and index "No Ischaemia",
            "Ischaemia".
    """

    
    ni_nb = x["ni_nb"]
    ni_b = x["ni_b"]
    i_nb = x["i_nb"]
    i_b = 1.0 - ni_nb - ni_b - i_nb
    
    data = {
        "No Bleed": [ni_nb, i_nb],
        "Bleed": [ni_b, i_b],
    }
    return DataFrame(data, index=["No Ischaemia", "Ischaemia"])

def simple_prob_input(parent, title: str, default_value: float) -> float:
    """Simple numerical input for setting probabilities

    Args:
        parent: The parent in which the number_input will be rendered
            (e.g. st)
        title: The name for the number_input (printed above the input box)
        default_value: The value to place in the number_input
    """
    return (
        parent.number_input(
            title,
            min_value=0.0,
            max_value=100.0,
            value=default_value,
            step=0.1,
        )
        / 100.0
    )
    
def simple_positive_input(parent, title: str, default_value: float, key: str = None) -> float:
    """Simple numerical input for setting positive values

    Args:
        parent: The parent in which the number_input will be rendered
            (e.g. st)
        title: The name for the number_input (printed above the input box)
        default_value: The value to place in the number_input.
        key: A unique value to distinguish this widget from others
    """
    
    if key is None:
        key = title
    
    return parent.number_input(
        title,
        min_value=0.0,
        value=default_value,
        step=0.1,
        key=key
    )