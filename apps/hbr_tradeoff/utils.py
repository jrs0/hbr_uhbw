"""Utilities for input/output in streamlit apps
"""

import streamlit as st
import numpy as np
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

def list_to_dataframe(x: list[float]) -> DataFrame:
    """Convert a list of probabilities to a table
    
    Similar to dict_to_dataframe, but constructs the dictionary from
    a list [ni_nb, ni_b, i_nb].
    
    Raises:
        ValueError if the input does not have length 3.
    
    Args:
        x: List of three items [ni_nb, ni_b, i_nb]
    
    Returns:
        A DataFrame with columns "No Bleed", "Bleed" and index "No Ischaemia",
            "Ischaemia".
    
    """
    if len(x) != 3:
        raise ValueError(f"Input list must have length 3; instead, it has length {len(x)}")
    
    d = {"ni_nb": x[0], "ni_b": x[1], "i_nb": x[2]}
    return dict_to_dataframe(d)

def scale_dependent_probs(
    probs: DataFrame, rr_ischaemia: float, rr_bleed: float
) -> DataFrame:
    """Scale non-independent probabilities of outcomes

    Based on an input probability of outcomes for the events
    (four probabilities, because bleeding and ischaemia are
    not independent), calculate the new probability of outcomes
    obtained by scaling the bleeding and ischaemia outcomes
    by risk ratios.

    The calculation is performed by assuming the risk ratios
    scale the probability of bleedin/ischaemia independently, so
    that the new probability of both adverse outcomes is
    rr_ischaemia * rr_bleed higher than the previous chance
    of both outcomes.

    The chance of just one outcome is then calculated by
    requiring that the new probability of a bleed is
    rr_bleed times higher than the old probability of
    a bleed (and similarly for ischaemia) -- this calculation
    uses the marginal probability of one outcome (i.e.
    adding up a row or column in the input and output
    dataframes).

    Args:
        probs: Table of probability of non-independent outcomes
            for bleeding and ischaemia (columns "No Bleed", "Bleed",
            index "No Ischaemia", "Ischaemia")
        rr_ischaemia: The relative risk of the high ischaemia risk group
        rr_bleed: The relative risk of the high bleeding risk group

    Raises:
        RuntimeError if probabilities in the input do not add up to one.

    Returns:
        A dataframe containing the new probabilities of ischaemia
            as the index and bleeding as the columns.
    """

    # Check that the input probabilities sum to 1.0
    total = probs.sum().sum()
    if np.abs(total - 1.0) > 1e-5:
        st.error(
            f"Total input probabilities must add up to 100%; these add up to {100*total:.2f}%"
        )

    # Get all the input variables separately
    ni_nb = probs.loc["No Ischaemia", "No Bleed"]
    ni_b = probs.loc["No Ischaemia", "Bleed"]
    i_nb = probs.loc["Ischaemia", "No Bleed"]
    i_b = probs.loc["Ischaemia", "Bleed"]

    # Assuming the independence of the risk ratios,
    # assume that the new chance of having both outcomes
    # is scaled. This formula comes from the similar formula
    # if the bleeding and ischaemia outcomes had been
    # independent:
    #
    # new_i_b = [rr_ischaemia * P(ischaemia)] * [rr_bleed * P(bleed)]
    #
    # In the non-independent case here, it is not true that
    # i_b = P(ischaemia) * P(bleeding)
    #
    new_i_b = rr_ischaemia * rr_bleed * i_b

    # This time, the marginals (probability of total ischaemia
    # and total bleeding) are assumed to scale with the individual
    # risk ratios. First, for total ischaemia probability:
    i = i_nb + i_b  # Old P(ischaemia)
    new_i = rr_ischaemia * i
    new_i_nb = new_i - new_i_b

    # And for the total bleeding marginal in the HBR/HIR group
    b = ni_b + i_b  # Old P(bleed)
    new_b = rr_bleed * b
    new_ni_b = new_b - new_i_b

    # Finally, the new chance of neither event is obtained by requiring
    # all the probabilities to add up to 1.0
    new_ni_nb = 1.0 - new_ni_b - new_i_nb - new_i_b

    # No need to check sum to one here because they do by construction
    # of the previous line.
    return dict_to_dataframe({"ni_nb": new_ni_nb, "ni_b": new_ni_b, "i_nb": new_i_nb})


def simple_auc(tpr: float, tnr: float) -> float:
    """Simple estimate of required AUC

    Assuming a ROC curve that passes through one point defined by
    the give true-positive and true-negative rates, calculate the
    area under the piecewise-linear ROC curve.

    A ROC curve is a plot of the true-positive rate on the y-axis
    against the false-positive rate (1 - true-negative rate) on
    the x-axis.

    Args:
        tpr: True-positive rate.
        tnr: True-negative rate.

    Returns:
        The required estimated AUC
    """
    # Calculate each area component
    middle_rect = tnr * tpr  # note x-axis is inverted
    left_triangle = 0.5 * (1 - tnr) * tpr
    right_triangle = 0.5 * tnr * (1 - tpr)
    return middle_rect + left_triangle + right_triangle


def get_ppv(fpr: float, fnr: float, prev: float) -> float:
    """Calculate the positive predictive value.

    The positive predictive value is the probability that
    a positive prediction is correct. It is defined by

    PPV = N(correctly predicted positive) / N(all predicted positive)

    It can be written as:

    PPV = P(correctly predicted positive) / [P(correctly predicted positive) + P(wrongly predicted positive)]

    Those terms can be calculated using the true/false positive
    rates and the prevalence, using:

    P(correctly predicted positive) = TPR * P(being positive)
    P(wrongly predicted positive) = FPR * P(being negative)

    The rates P(being positive) and P(being negative) are the
    prevalence and 1-prevalence.

    Args:
        fpr: False positive rate
        fnr: False negative rate
        prev: Prevalence

    Returns:
        The positive predictive value.
    """
    tpr = 1 - fnr
    p_correct_pos = tpr * prev
    p_wrong_pos = fpr * (1 - prev)
    return p_correct_pos / (p_correct_pos + p_wrong_pos)


def get_npv(fpr: float, fnr: float, prev: float) -> float:
    """Calculate the negative predictive value.

    The negative predictive value is the probability that
    a negative prediction is correct. It is defined by

    NPV = N(correctly predicted negative) / N(all predicted negative)

    It can be written as:

    NPV = P(correctly predicted negative) / [P(correctly predicted negative) + P(wrongly predicted negative)]

    Those terms can be calculated using the true/false negative
    rates and the prevalence, using:

    P(correctly predicted negative) = TNR * P(being negative)
    P(wrongly predicted negative) = FNR * P(being positive)

    The rates P(being positive) and P(being negative) are the
    prevalence and 1-prevalence.

    Args:
        fpr: False positive rate
        fnr: False negative rate
        prev: Prevalence

    Returns:
        The negative predictive value.
    """
    tnr = 1 - fpr
    p_correct_neg = tnr * (1 - prev)
    p_wrong_neg = fnr * prev
    return p_correct_neg / (p_correct_neg + p_wrong_neg)


def get_fpr(ppv: float, npv: float, prev: float) -> float:
    """Calculate the false positive rate.

    The false positive rate is the probability that a patient
    who is negative will be predicted positive. It is defined by:

    FPR = N(wrongly predicted positive) / N(all negative)

    Args:
        ppv: Positive predictive value
        npv: Negative predictive value
        prev: Prevalence

    Returns:
        The false positive rate
    """
    q = 1 - prev
    numerator = (q - npv) * (ppv - 1)
    denom = q * (ppv + npv - 1)
    return numerator / denom


def get_fnr(ppv: float, npv: float, prev: float) -> float:
    """Calculate the false negative rate.

    The false negative rate is the probability that a patient
    who is positive will be predicted negative. It is defined by:

    FNR = N(wrongly predicted negative) / N(all postive)

    Args:
        ppv: Positive predictive value
        npv: Negative predictive value
        prev: Prevalence

    Returns:
        The false positive rate
    """
    numerator = (prev - ppv) * (npv - 1)
    denom = prev * (ppv + npv - 1)
    return numerator / denom