# Bleeding/Ischaemia Risk Trade-off Models
#
# This is a script about different approaches to assessing
# the potential changes in outcomes due to modifications in
# therapy based on a bleeding/ischaemia risk trade-off tool,
# under different probability models of the underlying outcomes.
#
# The purpose is to understand what effects could be expected,
# and what side-effects may occur in the ischaemia outcomes as
# a result of attempting to reduce bleeding risk.
#
# The underlying framework for these calculations is as follows:
#
# - Patients are divided into a group where the bleeding/ischaemia
#   risk tool is used (A) and one where it is not (B).
# - The overall goal is to reduce severe bleeding complications,
#   under the hypothesis that ischaemia outcomes are already quite
#   well managed. As a result, it is a success is the group A has
#   less bleeding outcomes than group B, without there being an
#   increase in ischaemia outcomes. (An alternative possibility
#   would be to allow an increase in ischaemia outcomes, provided
#   that it is less than the reduction in count of bleeding
#   outcomes.)
#
# The following prevalences of outcomes following ACS/PCI will
# be assumed (corresponding to group B):
#
# NI + NB: 80%
# I + NB: 18%
# NI + B: 1%
# I + B: 1%
#
# Success of the intervention used in group A is defined by
# a reduction in the rate of * + B outcomes, that comes with
# no increase in total I + * outcomes.

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

st.title("Deterministic Model")
st.write("*Baseline patients are assumed to have determinsitic outcomes, which have a chance of being modified by the intervention.*")

st.write(
    "This page contains a simple theoretical model to estimate the effect of using a bleeding/ischaemia risk estimation tool selectively intervene in PCI patients to reduce their bleeding risk."
)
st.write(
    "In this model, patients are assumed to have predetermined outcomes, which occur deterministically in proportions which match the observed prevalence of bleeding and ischaemia outcomes (**Input 1**)."
)
st.write(
    "In the model, a tool attempts to predict who will have adverse events, with a certain degree of success (**Input 2**). An intervention is applied to the patients determined to be at high bleeding risk."
)
st.write(
    "The intervention is assumed to remove a bleeding event with a particular probability, and add an ischaemia event with a particular probability (**Input 3**)."
)
st.write(
    "Using the baseline prevalence, the accuracy of the model, and the efficacy of the intervention, the expected change in outcome proportions can be calculated, and compared to the baseline prevalences."
)
st.write(
    "The usefulness of the tool depends on the absolute number of bleeding events removed and ischaemia events introduced."
)

baseline_container = st.container(border=True)
baseline_container.header("Input 1: Baseline Outcome Proportions", divider=True)
baseline_container.write(
    "Set the basline proportions of bleeding and ischaemia outcomes in PCI patients. This is the characteristics of a PCI population not having any intervention based on estimated bleeding/ischaemia risk."
)

p_b_ni_nb = (
    baseline_container.number_input(
        "Proportion with no ischaemia and no bleeding (%)",
        min_value=0.0,
        max_value=100.0,
        value=80.0,
        step=0.1,
    )
    / 100.0
)
p_b_i_nb = (
    baseline_container.number_input(
        "Proportion with ischaemia but no bleeding (%)",
        min_value=0.0,
        max_value=100.0,
        value=18.0,
        step=0.1,
    )
    / 100.0
)
p_b_ni_b = (
    baseline_container.number_input(
        "Proportion with bleeding but no ischaemia (%)",
        min_value=0.0,
        max_value=100.0,
        value=1.0,
        step=0.1,
    )
    / 100.0
)
p_b_i_b = (
    baseline_container.number_input(
        "Proportion with bleeding and ischaemia (%)",
        min_value=0.0,
        max_value=100.0,
        value=1.0,
    )
    / 100
)

total_prob = p_b_ni_nb + p_b_ni_b + p_b_i_nb + p_b_i_b
if np.abs(total_prob - 1.0) > 1e-5:
    st.error(
        f"Total proportions must add up to 100%; these add up to {100*total_prob:.2f}%"
    )


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


# DETERMINISTIC MODELS
#
# In the models below, it is assumed that the outcomes are deterministic
# in the group A, and the job of the prediction tool is to predict these
# outcomes so as to establish the group who will bleed, and apply an
# intervention to them.

# Model 0: Exact prediction of bleeding/ischaemia, intervention
# completely removes bleeding event (no effect on ischaemia)
#
# In this model, it is assumed that bleeding and ischaemia outcomes
# can be predicted exactly, and the intervention (modification of DAPT)
# is such that a bleeding outcome can be entirely (deterministically) removed
# without affecting the ischaemia outcome. No calculation is required to
# establish the outcomes under this model, because all * + B outcomes
# would be added to * + NB categories, resulting in:
#
p_a_ni_nb = p_b_ni_nb + p_b_ni_b
p_a_i_nb = p_b_i_nb + p_b_i_b
p_a_ni_b = 0
p_a_i_b = 0

# Model 1: Exact prediction of bleeding/ischaemia, intervention has
# probability p to remove bleeding event (no effect on ischaemia)
#
# In this model, it is assumed that a patient who will bleed is
# identified deterministically, but the intervention will only
# remove the bleeding event with probability p. However, the
# ischaemia event will not be modified.
#
p = 0.2
p_a_ni_nb = p_b_ni_nb + p * p_b_ni_b
p_a_i_nb = p_b_i_nb + p * p_b_i_b
p_a_ni_b = (1 - p) * p_b_ni_b
p_a_i_b = (1 - p) * p_b_i_b

# Model 2: Exact prediction of bleeding/ischaemia, intervention has
# probability p to remove bleeding event, and probability p to add
# ischaemia event
#
# In this model, bleeding events will be removed with some
# probability, but there is the same probability that an
# ischaemia event is introduced. Since the prediction of original
# outcome is exact (and therefore the intervention is highly
# tailored), there is no effect on outcomes in the group who would
# not bleed (98%)
#
# Here, the decrease in bleeding outweighs the increase in ischaemia
# in whatever proportional split there is between ischaemia and
# non ischaemia in the bleeding group. For example, for a split of
# 50%, bleeding reduced by twice as much as ischaemia increases
# (because all the bleeding events are subject to p, but only half
# of the ischaemia events are, the other half already having an
# ischaemia event.
#
p = 0.2
p_a_ni_nb = (
    p_b_ni_nb + p * (1 - p) * p_b_ni_b
)  # Bleeding removed and no ischaemia added
p_a_i_nb = (
    p_b_i_nb + p * p_b_i_b + p * p * p_b_ni_b
)  # Bleeding removed, and either ischaemia added or already present
p_a_ni_b = (1 - p) * (1 - p) * p_b_ni_b  # Bleeding and ischaema both unaffected
p_a_i_b = (1 - p) * p_b_i_b + (
    1 - p
) * p * p_b_ni_b  # Bleeding unaffected but ischaemia introduced

# Model 3: Inexact prediction of bleeding with probability q,
# intervention completely removes a bleeding event
# and has no effect on ischaemia outcomes
#
# In this model, all the bleeding events correctly predicted will
# be eliminated, and there is no possible adverse effect on ischaemia.
# Therefore, the proportion q of bleeding events will be eliminated,
# that is.
#
q = 0.8
p_a_ni_nb = p_b_ni_nb + q * p_b_ni_b
p_a_i_nb = p_b_i_nb + q * p_b_i_b
p_a_ni_b = (1 - q) * p_b_ni_b
p_a_i_b = (1 - q) * p_b_i_b

# Model 4: Inexact prediction of bleeding with probability q,
# intervention has probability p to remove bleeding event, and
# probability p to add ischaemia event
#
# Note that this model, like all the models above, applies the
# intervention only based on the prediction of bleeding (whether
# or not the patient is predicted to have further ischaemia is
# ignored).
#
# Here, by getting the prediction of bleeding wrong a proportion of
# the time, approximately that same proportion of patients will
# incorrectly receive an intervention that increases the ischaemia
# risk. Since the pool of bleeding patients is so small, it doesn't
# take much for the total ischaemia increase to outweigh the bleeding
# decrease.
#
# This model motivates consideration of an intervention that depends
# on both the ischaemia and risk prediction:
#
# - If predicted NI/B, apply main intervention X
# - If predicted I/B, apply intervention Y designed not to increase
#   ischaemia risk.
#
q = 0.7
p = 0.2

# - Previous NI/NB, (right) no intervention
# - Previous NI/NB, (wrong) intervention, no change in outcomes
# - Previous NI/B, (right) intervention, remove bleeding and no ischaemia change
p_a_ni_nb = q * p_b_ni_nb + (1 - q) * (1 - p) * p_b_ni_nb + q * p * (1 - p) * p_b_ni_b

# - Previous I/NB, (right) no intervention
# - Previous I/NB, (wrong) intervention, no change in outcomes
# - Previous I/B, (right) intervention, remove bleeding
# - Previous NI/NB, (wrong) intervention adds ischaemia
# - Previous NI/B, (right) intervention, remove bleeding but adds ischaemia
p_a_i_nb = (
    q * p_b_i_nb
    + (1 - q) * p_b_i_nb
    + (1 - q) * p * p_b_ni_nb
    + q * p * p * p_b_ni_b
    + q * p * p_b_i_b
)

# - Previous NI/B, (right) intervention, no change in bleeding/ischaemia
# - Previous NI/B, (wrong) no intervention
p_a_ni_b = q * (1 - p) * (1 - p) * p_b_ni_b + (1 - q) * p_b_ni_b

# - Previous I/B, (right) intervention, no change in bleeding
# - Previous I/B, (wrong) no intervention
# - Previous NI/B, (right) intervention, no change in bleeding but adds ischaemia
p_a_i_b = q * (1 - p) * p_b_i_b + (1 - q) * p_b_i_b + q * (1 - p) * p * p_b_ni_b

# Model 5: Full Deterministic Model
#
# In this model, predictions are made for whether the patient will have bleeding
# or ischaemia events, which have probability of success q_b and q_i. Two
# possible intervention are made depending on the results of the prediction:
#
# NI/B: Intervention X, reduces bleeding risk by p_x and increase
#     ischaemia risk by p_x. The rationale is that the patient is at low
#     ischaemia risk, so a more aggressive intervention (such as lowering
#     DAPT) is possible to reduce bleeding risk
# I/B: Intervention Y, reduces bleeding risk by p_y (where p_y < p_x), and
#     does not modify ischaemia risk. This is a less aggressive intervention,
#     such as notifying relevant clinicians and the patient of the high bleeding
#     risk, but not modifying DAPT medication, so that the ischaemia risk is
#     not increased. Due to the less aggressive intervention, the probability
#     of removing the bleeding event is less compared to X.
# */NB: Do not intervene (depends only on bleeding prediction)
#
# To make the interventions more general, use the following notation:
#
# X: P(remove bleeding) = x_b, P(add ischaemia) = x_i
# Y: P(remove bleeding) = y_b, P(add ischaemia) = y_i
#
# Note that both X and Y can only reduce bleeding and increase ischaemia
# in this model. Note also that X and Y are mutually exclusive.
#
# Notethat splitting the interventions into X and Y in this model
# may be misleading, because those in the ideal Y group have a deterministic
# ischaemia event anyway, so there is no improvement due to the reduced
# intensity of Y. If the model included a model of patient risk which is
# modified by the interventions X and Y, then the reduced intensity of
# Y would be beneficial (this also matches reality better). Paradoxically,
# in this model, it is the people predicted to have no ischaemia which
# should be given the less intensive therapy -- this is just a defect
# of the model.
#


st.write(
    "A group of patients have their bleeding/ischaemia risk estimated by a tool (assumed to be a black box). In this model, the tool attempts to predict the bleeding/ischaemia outcomes a patient will have."
)
st.write(
    "The accuracy of the tool is characterised by the true positive and true negative rates, comparing the outcome prediction by the model to what outcome will actually occur."
)
st.info(
    "Because patient outcomes in this model are assumed to be deterministic, a high-risk patient is defined as one who is predicted to have an adverse outcome occur.",
    icon="ℹ️",
)  # Warning, i is a funny character!

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
    st.session_state["q_b_tpr"] = (
        model_columns[0].number_input(
            "True-positive rate (%)",
            key="input_q_b_tpr",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["q_b_tpr"],
            step=0.1,
            help="The true-positive rates determine how well high-bleeding-risk patients are picked up. A high number will increase the chance of making targetted reductions in bleeding patients.",
        )
        / 100.0
    )
    st.session_state["q_b_tnr"] = (
        model_columns[0].number_input(
            "True-negative rate (%)",
            key="input_q_b_tnr",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["q_b_tnr"],
            step=0.1,
            help="A high true-negative rate is the same as a low false-positive rate, which reduces low-risk patients being exposed to an intervention unnecessarily.",
        )
        / 100.0
    )
else:
    st.session_state["q_b_tpr"] = 1 - (
        model_columns[0].number_input(
            "False-negative rate (%)",
            key="input_q_b_fnr",
            min_value=0.0,
            max_value=100.0,
            value=100 * (1 - st.session_state["q_b_tpr"]),
            step=0.1,
            help="A low false-negative rate is the same as a high true-positive rate, which increases the chance of identifting high-bleedin-risk patients who require intervention.",
        )
        / 100.0
    )
    st.session_state["q_b_tnr"] = 1 - (
        model_columns[0].number_input(
            "False-positive rate (%)",
            key="input_q_b_fpr",
            min_value=0.0,
            max_value=100.0,
            value=100 * (1 - st.session_state["q_b_tnr"]),
            step=0.1,
            help="A low false-positive rate prevents low-bleeding-risk patients being exposed to an intervention unnecessarily.",
        )
        / 100.0
    )

model_columns[1].subheader("Ischaemia Model")
model_columns[1].write(
    "Set the ischaemia model's ability to identify high- and low-risk patients."
)

# Get true-positive/true-negative rates for the bleeding model from the user
if not use_negative_rates:
    st.session_state["q_i_tpr"] = (
        model_columns[1].number_input(
            "True-positive rate (%)",
            key="input_q_i_tpr",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["q_i_tpr"],
            step=0.1,
            help="The true-positive rates determine how well high-ischaemia-risk patients are picked up. A high number will increase the chance of making targetted reductions in bleeding patients.",
        )
        / 100.0
    )
    st.session_state["q_i_tnr"] = (
        model_columns[1].number_input(
            "True-negative rate (%)",
            key="input_q_i_tnr",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["q_i_tnr"],
            step=0.1,
            help="A high true-negative rate is the same as a low false-positive rate, which reduces low-ischaemia-risk patients being exposed to an intervention unnecessarily.",
        )
        / 100.0
    )
else:
    st.session_state["q_i_tpr"] = 1 - (
        model_columns[1].number_input(
            "False-negative rate (%)",
            key="input_q_i_fnr",
            min_value=0.0,
            max_value=100.0,
            value=100 * (1 - st.session_state["q_i_tpr"]),
            step=0.1,
            help="A low false-negative rate is the same as a high true-positive rate, which increases the chance of identifting high-ischaemia-risk patients who require intervention.",
        )
        / 100.0
    )
    st.session_state["q_i_tnr"] = 1 - (
        model_columns[1].number_input(
            "False-positive rate (%)",
            key="input_q_i_fpr",
            min_value=0.0,
            max_value=100.0,
            value=100 * (1 - st.session_state["q_i_tnr"]),
            step=0.1,
            help="A low false-positive rate prevents low-ischaemia-risk patients being exposed to an intervention unnecessarily.",
        )
        / 100.0
    )

# Expose the model accuracies as variables for convenience
q_b_tpr = st.session_state["q_b_tpr"]
q_b_tnr = st.session_state["q_b_tnr"]
q_i_tpr = st.session_state["q_i_tpr"]
q_i_tnr = st.session_state["q_i_tnr"]

roc_expander = st.expander(
    "**What ROC Curve would achieve this accuracy?**", expanded=False
)

roc_container = roc_expander.container(border=True)
roc_container.header("Required ROC Curves", divider=True)
roc_container.write(
    "The ROC curve is a plot of true-positive rate on the y-axis against false-positive rate on the x-axis, for various thresholds that might be used to decide that a patient is high risk."
)
roc_container.write(
    "The accuracy specification above determines a single coordinate on this plot, which the ROC curve must pass though if the model is to have the required accuracy. Better models will require the ROC curve to pass through a point near the top-left corner."
)
roc_container.write(
    "The area under the ROC curve (AUC) is only relevant insofar as a ROC curve passing through a point near the top-left corner will likely have a high AUC."
)
roc_container.write(
    "Below, two hypothetical ROC curves are plotted (one for the bleeding model and one for the ischaemia model), which pass through the required points."
)

fig, ax = plt.subplots()


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


# Plot baseline
ax.plot([0.0, 100], [0.0, 100], "--")

# Bleeding model ROC
data = {"x": [0.0, 100 * (1 - q_b_tnr), 100.0], "y": [0.0, 100 * q_b_tpr, 100.0]}
auc = simple_auc(q_b_tpr, q_b_tnr)
ax.plot(data["x"], data["y"], color="r", label=f"Bleeding model (AUC > {auc:.2f})")
ax.fill_between(data["x"], data["y"], [0.0] * 3, color="r", alpha=0.05)

# Ischaemia model ROC
data = {"x": [0.0, 100 * (1 - q_i_tnr), 100.0], "y": [0.0, 100 * q_i_tpr, 100.0]}
auc = simple_auc(q_i_tpr, q_i_tnr)
ax.plot(data["x"], data["y"], color="b", label=f"Ischaemia model (AUC > {auc:.2f})")
ax.fill_between(data["x"], data["y"], [0.0] * 3, color="b", alpha=0.05)

ax.set_xlabel("False-positive rate (%)")
ax.set_ylabel("True-positive rate (%)")
ax.set_title("Bleeding Model")
ax.legend(loc="lower right")

roc_container.pyplot(fig)
roc_container.write(
    "The ROC AUC is calculated for the minimum convex shapes that pass through the required point. A more realistic ROC curve that passes through the point would likely have a slightly higher area, due to the extra curvature in the straight segments."
)


st.write(
    "When the tool predicts a bleed, one of two interventions are made. If no ischaemia is predicted, an aggressive intervention $X$ is made (e.g. a change in DAPT therapy), which has $X_b\%$ chance to remove a bleeding event, and $X_i\%$ chance to add an ischaemia event."
)
st.write(
    "If, however, ischaemia is also predicted, then a less aggressive intervention $Y$ is made (e.g. no modification of therapy, but advice to the clinicians and patients that bleeding risk is high. It has chance $Y_b\%$ to remove a bleeding event, and $Y_i\%$ chance to add an ischaemia event."
)

intervention_container = st.container(border=True)
intervention_container.header("Input 3: Intervention Effectiveness", divider=True)
intervention_container.write(
    "Set the probabilities for each intervention to reduce bleeding, and increase ischaemia."
)
intervention_container.write(
    "In this model, an intervention can only reduce the chance of bleeding, and can only increase the chance of ischaemia."
)
x_and_y_separate = intervention_container.toggle(
    "Y is different from X",
    value=False,
    help="By default, only one intervention $X$ is used on all high bleeding risk patients. Click here to allow use of a different intervention $Y$ for when a patient is flagged as high-ischaemia risk.",
)

# Set default intervention effectiveness
if "x_b" not in st.session_state:
    st.session_state["x_b"] = 0.5
if "x_i" not in st.session_state:
    st.session_state["x_i"] = 0.5
if "y_b" not in st.session_state:
    st.session_state["y_b"] = 0.5
if "y_i" not in st.session_state:
    st.session_state["y_i"] = 0.5

if not x_and_y_separate:
    st.session_state["x_b"] = (
        intervention_container.number_input(
            "Probability that a bleeding event is removed (%)",
            key="input_xy_b",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["x_b"],
            step=0.1,
        )
        / 100.0
    )
    st.session_state["y_b"] = st.session_state["x_b"]
    st.session_state["x_i"] = (
        intervention_container.number_input(
            "Probability that an ischaemia event is introduced (%)",
            key="input_xy_i",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["x_i"],
            step=0.1,
        )
        / 100.0
    )
    st.session_state["y_i"] = st.session_state["x_i"]
else:
    intervention_columns = intervention_container.columns(2)
    intervention_columns[0].subheader("Intervention $X$")
    intervention_columns[1].subheader("Intervention $Y$")
    st.session_state["x_b"] = (
        intervention_columns[0].number_input(
            "Probability that a bleeding event is removed (%)",
            key="input_x_b",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["x_b"],
            step=0.1,
        )
        / 100.0
    )
    st.session_state["x_i"] = (
        intervention_columns[0].number_input(
            "Probability that an ischaemia event is removed (%)",
            key="input_x_i",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["x_i"],
            step=0.1,
        )
        / 100.0
    )
    st.session_state["y_b"] = (
        intervention_columns[1].number_input(
            "Probability that a bleeding event is removed (%)",
            key="input_y_b",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["y_b"],
            step=0.1,
        )
        / 100.0
    )
    st.session_state["y_i"] = (
        intervention_columns[1].number_input(
            "Probability that an ischaemia event is removed (%)",
            key="input_y_i",
            min_value=0.0,
            max_value=100.0,
            value=100 * st.session_state["y_i"],
            step=0.1,
        )
        / 100.0
    )

# Get the variables for convenience
x_b = st.session_state["x_b"]
x_i = st.session_state["x_i"]
y_b = st.session_state["y_b"]
y_i = st.session_state["y_i"]

st.write(
    "Based on the inputs above, there is a probability that a patient's outcomes will be correctly predicted, and a probability that an intervention to reduce bleeding will be successful (i.e. reduce bleeding and not increase ischaemia)."
)
st.write(
    "There will also be patients who would not have had any adverse event, but which are flagged as high bleeding risk and have an intervention which introduces ischaemia."
)
st.write("The balance between these two competing effects is calculated below.")

# Probabilities of each outcome are worked out below. Note that
# X and Y can only reduce bleeding and increase ischaemia, which
# narrows the options for what can have led to a given outcome.
# In this deterministic model, if no intervention is performed,
# the outcome does not change.

# True-positive rates (TPR) and true-negative rates (TNR) are used to calculate
# the probability of having an outcome predicted correctly. These
# are the correct numbers to use, because the TPR (TNR) is the probability
# of the test being correct given that a patient is positive (negative) --
# see the wiki page for sensitivity and specificity (alternative names for
# TPR and TNR).
#
# The PPV/NPV are not relevant for the calculations below, because each term
# corresponds to a set of patients who are all-positive or all-negative (not
# a mixture).

# Previous NI/NB, correct no intervene
a_0 = q_b_tnr * p_b_ni_nb
# Previous NI/NB, incorrect X, bleeding already none, no increase in ischaemia
a_1 = q_i_tnr * (1 - q_b_tnr) * (1 - x_i) * p_b_ni_nb
# Previous NI/NB, incorrect Y, bleeding already none, no increase in ischaemia
a_2 = (1 - q_i_tnr) * (1 - q_b_tnr) * (1 - y_i) * p_b_ni_nb
# Previous NI/B, correct X, bleeding was removed, no increase in ischaemia
a_3 = q_i_tnr * q_b_tpr * x_b * (1 - x_i) * p_b_ni_b
# Previous NI/B, incorrect Y, bleeding was removed, no increase in ischaemia
a_4 = (1 - q_i_tnr) * q_b_tpr * y_b * (1 - y_i) * p_b_ni_b
# Add up all the terms
p_a_ni_nb = a_0 + a_1 + a_2 + a_3 + a_4

# Previous NI/B, incorrect no intervene
a_0 = (1 - q_b_tpr) * p_b_ni_b
# Previous NI/B, incorrect Y, no reduction in bleeding/increase in ischaemia
a_1 = (1 - q_i_tnr) * q_b_tpr * (1 - y_i) * (1 - y_b) * p_b_ni_b
# Previous NI/B, correct X, no reduction in bleeding/increase in ischaemia
a_2 = q_i_tnr * q_b_tpr * (1 - x_i) * (1 - x_b) * p_b_ni_b
# Add up all the terms
p_a_ni_b = a_0 + a_1 + a_2

# Previous I/NB, any action (nothing affects the outcome)
a_0 = p_b_i_nb
# Previous NI/NB, incorrect X, bleeding already none, increase in ischaemia
a_1 = q_i_tnr * (1 - q_b_tnr) * x_i * p_b_ni_nb
# Previous NI/NB, incorrect Y, bleeding already none, increase in ischaemia
a_2 = (1 - q_i_tnr) * (1 - q_b_tnr) * y_i * p_b_ni_nb
# Previous I/B, correct Y, ischaemia already present, reduces bleeding
a_3 = q_i_tpr * q_b_tpr * y_b * p_b_i_b
# Previous I/B, incorrect X, ischaemia already present, reduces bleeding
a_4 = (1 - q_i_tpr) * q_b_tpr * x_b * p_b_i_b
# Previous NI/B, incorrect Y, ischaemia added, reduces bleeding
a_5 = (1 - q_i_tnr) * q_b_tpr * y_i * x_b * p_b_ni_b
# Previous NI/B, correct X, ischaemia added, reduces bleeding
a_6 = q_i_tnr * q_b_tpr * x_i * x_b * p_b_ni_b
# Add up all the terms
p_a_i_nb = a_0 + a_1 + a_2 + a_3 + a_4 + a_5 + a_6

# Previous I/B, incorrect no intervene
a_0 = (1 - q_b_tpr) * p_b_i_b
# Previous I/B, correct Y, ischaemia already present, no reduction in bleeding
a_1 = q_i_tpr * q_b_tpr * (1 - y_b) * p_b_i_b
# Previous I/B, incorrect X, ischaemia already present, no reduction in bleeding
a_2 = (1 - q_i_tpr) * q_b_tpr * (1 - x_b) * p_b_i_b
# Previous NI/B, incorrect Y, ischaemia added, no reduction in bleeding
a_3 = (1 - q_i_tnr) * q_b_tpr * y_i * (1 - y_b) * p_b_ni_b
# Previous NI/B, correct X, ischaemia added, no reduction in bleeding
a_4 = q_i_tnr * q_b_tpr * x_i * (1 - x_b) * p_b_ni_b
# Add up all the terms
p_a_i_b = a_0 + a_1 + a_2 + a_3 + a_4

# Do a sanity check
total_prob = p_a_ni_nb + p_a_i_nb + p_a_ni_b + p_a_i_b
if np.abs(total_prob - 1.0) > 1e-7:
    raise RuntimeError("Invalid total probability {total_prob} in output prevalence")

output_container = st.container(border=True)
output_container.header("Output: Outcome Proportions using Tool", divider=True)

output_container.write(
    "To make the outcome concretely interpretable in terms of numbers of patients, choose a number of patients $N$ who will undergo PCI and potentially receive a therapy intervention using the tool:"
)

n = output_container.number_input(
    "Number of PCI patients treated using risk estimation tool",
    min_value=0,
    max_value=10000,
    value=5000,
)

bleeding_before = int(n * (p_b_i_b + p_b_ni_b))
bleeding_after = int(n * (p_a_i_b + p_a_ni_b))
ischaemia_before = int(n * (p_b_i_b + p_b_i_nb))
ischaemia_after = int(n * (p_a_i_b + p_a_i_nb))

output_container.write(
    "In this theoretical model, bleeding and ischaemia events are considered equally severe, so success is measured by counting the number of bleeding events reduced and comparing it in absolute terms to the number of ischaemia events added."
)

output_container.write(
    f"**Expected changes in outcomes of a pool of {n} patients, compared to baseline**"
)

bleeding_increase = int(bleeding_after - bleeding_before)
ischaemia_increase = ischaemia_after - ischaemia_before
previous_adverse_outcomes = bleeding_before + ischaemia_before
total_adverse_outcomes = bleeding_after + ischaemia_after
outcome_difference = total_adverse_outcomes - previous_adverse_outcomes

col1, col2, col3 = output_container.columns(3)
col1.metric("Bleeding", bleeding_after, bleeding_increase, delta_color="inverse")
col2.metric("Ischaemia", ischaemia_after, ischaemia_increase, delta_color="inverse")
col3.metric("Total Adverse Outcomes", total_adverse_outcomes, outcome_difference, delta_color="inverse")
