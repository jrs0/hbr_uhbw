"""Collection of inputs for streamlit apps

Functions are collected here because they are sometimes 
reused across the various model versions (e.g. baseline
outcome prevalences).
"""

import numpy as np
import streamlit as st
from pandas import DataFrame
import utils

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
    ni_nb = simple_prob(
        parent, "Proportion with no ischaemia and no bleeding (%)", 100*default_ni_nb
    )
    i_nb = simple_prob(
        parent, "Proportion with ischaemia but no bleeding (%)", 100*default_i_nb
    )
    ni_b = simple_prob(
        parent, "Proportion with bleeding but no ischaemia (%)", 100*default_ni_b
    )
    i_b = simple_prob(
        parent, "Proportion with bleeding and ischaemia (%)", 100*default_i_b
    )

    # Check user-inputted probabilities sum to 1.0
    total = ni_nb + ni_b + i_nb + i_b
    if np.abs(total - 1.0) > 1e-5:
        st.error(
            f"Total proportions must add up to 100%; these add up to {100*total:.2f}%"
        )

    return utils.dict_to_dataframe({"ni_nb": ni_nb, "ni_b": ni_b, "i_nb": i_nb})


def simple_prob(parent, title: str, default_value: float, key=None, help=None) -> float:
    """Simple numerical input for setting probabilities

    Args:
        parent: The parent in which the number_input will be rendered
            (e.g. st)
        title: The name for the number_input (printed above the input box)
        default_value: The value to place in the number_input
        key: An optional key, in case you need to avoid duplicate elements (this
            happens when two elements have the same title)
        help: An optional help message to display on the input
    """
    return (
        parent.number_input(
            title,
            key=key,
            help=help,
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

def model_accuracy() -> dict[str, float]:
    """Get the model accuracy from the user as true positive/negative rates

    Returns:
        A dictionary of items containing "tpr_b" (true positive rate for
            bleeding), "tnr_b" (true negative rate for bleeding), and
            "tpn_i" and "tnr_i" for ischaemia
    """
    model_container = st.container(border=True)
    model_container.header("Input 2: Model Accuracy", divider=True)

    model_container.write(
        "Set the true-positive and true-negative rates for the models predicting each outcome. Alternatively (equivalently), choose to input false-positive and false-negative rates."
    )

    use_negative_rates = model_container.toggle(
        "Use Negative Rates",
        value=False,
        help="Choose whether to input true-positive/negative rates or false-positive/negative rates. True-positive and false-negative rates (being all predictions out of a group who are definitely positive) add up to 100%; similarly, true-negative and false-positive rates add up to 100%.",
    )

    model_columns = model_container.columns(2)

    # Set default true-positive/true-negative values
    if "q_b_tpr" not in st.session_state:
        st.session_state["q_b_tpr"] = 0.8
    if "q_b_tnr" not in st.session_state:
        st.session_state["q_b_tnr"] = 0.8
    if "q_i_tpr" not in st.session_state:
        st.session_state["q_i_tpr"] = 0.85
    if "q_i_tnr" not in st.session_state:
        st.session_state["q_i_tnr"] = 0.85

    model_columns[0].subheader("Bleeding Model")
    model_columns[0].write(
        "Set the bleeding model's ability to identify high- and low-risk patients."
    )

    # Get true-positive/true-negative rates for the bleeding model from the user
    if not use_negative_rates:
        st.session_state["q_b_tpr"] = simple_prob(
            model_columns[0],
            "True-positive rate (%)",
            key="input_q_b_tpr",
            default_value=100 * st.session_state["q_b_tpr"],
            help="The true-positive rates determine how well high-bleeding-risk patients are picked up. A high number will increase the chance of making targetted reductions in bleeding patients.",
        )
        st.session_state["q_b_tnr"] = simple_prob(
            model_columns[0],
            "True-negative rate (%)",
            key="input_q_b_tnr",
            default_value=100 * st.session_state["q_b_tnr"],
            help="A high true-negative rate is the same as a low false-positive rate, which reduces low-risk patients being exposed to an intervention unnecessarily.",
        )
    else:
        st.session_state["q_b_tpr"] = 1 - simple_prob(
            model_columns[0],
            "False-negative rate (%)",
            key="input_q_b_fnr",
            default_value=100 * (1 - st.session_state["q_b_tpr"]),
            help="A low false-negative rate is the same as a high true-positive rate, which increases the chance of identifting high-bleedin-risk patients who require intervention.",
        )
        st.session_state["q_b_tnr"] = 1 - simple_prob(
            model_columns[0],
            "False-positive rate (%)",
            key="input_q_b_fpr",
            default_value=100 * (1 - st.session_state["q_b_tnr"]),
            help="A low false-positive rate prevents low-bleeding-risk patients being exposed to an intervention unnecessarily.",
        )

    model_columns[1].subheader("Ischaemia Model")
    model_columns[1].write(
        "Set the ischaemia model's ability to identify high- and low-risk patients."
    )

    # Get true-positive/true-negative rates for the bleeding model from the user
    if not use_negative_rates:
        st.session_state["q_i_tpr"] = simple_prob(
            model_columns[1],
            "True-positive rate (%)",
            key="input_q_i_tpr",
            default_value=100 * st.session_state["q_i_tpr"],
            help="The true-positive rates determine how well high-ischaemia-risk patients are picked up. A high number will increase the chance of making targetted reductions in bleeding patients.",
        )
        st.session_state["q_i_tnr"] = simple_prob(
            model_columns[1],
            "True-negative rate (%)",
            key="input_q_i_tnr",
            default_value=100 * st.session_state["q_i_tnr"],
            help="A high true-negative rate is the same as a low false-positive rate, which reduces low-ischaemia-risk patients being exposed to an intervention unnecessarily.",
        )

    else:
        st.session_state["q_i_tpr"] = 1 - simple_prob(
            model_columns[1],
            "False-negative rate (%)",
            key="input_q_i_fnr",
            default_value=100 * (1 - st.session_state["q_i_tpr"]),
            help="A low false-negative rate is the same as a high true-positive rate, which increases the chance of identifting high-ischaemia-risk patients who require intervention.",
        )
        st.session_state["q_i_tnr"] = 1 - simple_prob(
            model_columns[1],
            "False-positive rate (%)",
            key="input_q_i_fpr",
            default_value=100 * (1 - st.session_state["q_i_tnr"]),
            help="A low false-positive rate prevents low-ischaemia-risk patients being exposed to an intervention unnecessarily.",
        )

    # Expose the model accuracies as variables for convenience
    return {
        "tpr_b": st.session_state["q_b_tpr"],
        "tnr_b": st.session_state["q_b_tnr"],
        "tpr_i": st.session_state["q_i_tpr"],
        "tnr_i": st.session_state["q_i_tnr"],
    }