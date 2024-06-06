"""Collection of inputs for streamlit apps

Functions are collected here because they are sometimes 
reused across the various model versions (e.g. baseline
outcome prevalences).
"""

import numpy as np
import streamlit as st
from pandas import DataFrame
import utils
import inputs

def prevalences(parent, defaults: dict[str, float]) -> DataFrame:
    """User input for non-independent proportions of outcomes

    Use this function to get (e.g. baseline) proportions of bleeding
    and ischaemia outcomes, assuming the outcomes are not independent.
    As a result, four probabilities must be given by the user, one for
    each combination of outcomes.

    Args:
        parent: The streamlit container in which to place the input
        defaults: Map from the keys "ni_nb", "ni_b", "i_nb"
            to the proportion of each outcome. The final combination
            "i_b" is calculated assuming they all sum to 1.0.

    Returns:
        A table containing the probability of each outcome. The columns
            are "No Bleed" and "Bleed", and the index is "No Ischaemia"
            and "Ischaemia".
    """

    # Calculate the final default value based on sum to 1.0
    default_ni_nb = defaults["ni_nb"]
    default_ni_b = defaults["ni_b"]
    default_i_nb = defaults["i_nb"]
    default_i_b = 1.0 - default_ni_nb - default_ni_b - default_i_nb

    # Get the user inputs
    ni_nb = inputs.simple_prob(
        parent, "Proportion with no ischaemia and no bleeding (%)", 100*default_ni_nb
    )
    i_nb = inputs.simple_prob(
        parent, "Proportion with ischaemia but no bleeding (%)", 100*default_i_nb
    )
    ni_b = inputs.simple_prob(
        parent, "Proportion with bleeding but no ischaemia (%)", 100*default_ni_b
    )
    i_b = inputs.simple_prob(
        parent, "Proportion with bleeding and ischaemia (%)", 100*default_i_b
    )

    # Check user-inputted probabilities sum to 1.0
    total = ni_nb + ni_b + i_nb + i_b
    if np.abs(total - 1.0) > 1e-5:
        st.error(
            f"Total proportions must add up to 100%; these add up to {100*total:.2f}%"
        )

    return utils.dict_to_dataframe({"ni_nb": ni_nb, "ni_b": ni_b, "i_nb": i_nb})


def simple_prob(parent, title: str, default_value: float) -> float:
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


def simple_positive(
    parent, title: str, default_value: float, key: str = None
) -> float:
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
        title, min_value=0.0, value=default_value, step=0.1, key=key
    )
