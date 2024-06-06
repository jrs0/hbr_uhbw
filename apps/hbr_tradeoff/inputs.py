"""Collection of inputs for streamlit apps

Functions are collected here because they are sometimes 
reused across the various model versions (e.g. baseline
outcome prevalences).
"""

import numpy as np
import streamlit as st
from pandas import DataFrame
from utils import dict_to_dataframe, simple_prob_input

def input_prevalences(parent, defaults: dict[str, float]) -> DataFrame:
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
    ni_nb = simple_prob_input(
        parent, "Proportion with no ischaemia and no bleeding (%)", 100*default_ni_nb
    )
    i_nb = simple_prob_input(
        parent, "Proportion with ischaemia but no bleeding (%)", 100*default_i_nb
    )
    ni_b = simple_prob_input(
        parent, "Proportion with bleeding but no ischaemia (%)", 100*default_ni_b
    )
    i_b = simple_prob_input(
        parent, "Proportion with bleeding and ischaemia (%)", 100*default_i_b
    )

    # Check user-inputted probabilities sum to 1.0
    total = ni_nb + ni_b + i_nb + i_b
    if np.abs(total - 1.0) > 1e-5:
        st.error(
            f"Total proportions must add up to 100%; these add up to {100*total:.2f}%"
        )

    return dict_to_dataframe({"ni_nb": ni_nb, "ni_b": ni_b, "i_nb": i_nb})


    