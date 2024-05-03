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

import streamlit as st

st.title("Bleeding Ischaemia Trade-Off")

st.write(
    "Set the basline proportions of bleeding and ischaemia outcomes in PCI patients (with no HBR intervention) (make sure all the numbers are positive; will be fixed soon)."
)

p_b_ni_nb = (
    st.slider(
        "Baseline P(NI and NB)",
        min_value=0.0,
        max_value=100.0,
        value=80.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
p_b_i_nb = (
    st.slider(
        "Baseline P(I and NB)",
        min_value=0.0,
        max_value=100.0,
        value=18.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
p_b_ni_b = (
    st.slider(
        "Baseline P(NI and B)",
        min_value=0.0,
        max_value=100.0,
        value=1.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
p_b_i_b = 1.0 - p_b_ni_nb - p_b_i_nb - p_b_ni_b
st.slider(
    "P(I and B)",
    min_value=0.0,
    max_value=100.0,
    value=100 * p_b_i_b,
    format=f"%.2f%%",
    disabled=True,
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

st.write("In this model, patients in the baseline (no intervention) group are assumed to have deterministic outcomes. A hypothetical tool is used to predict these outcomes. The tool is correct $Q_b\%$ of the time when predicting bleeding, and $Q_i\%$ of the time when predicting ischaemia (not overall; separately for both positive and negative predictions).")
st.write("When the tool predicts a bleed, one of two interventions are made. If no ischaemia is predicted, an aggressive intervention X is made (e.g. a change in DAPT therapy), which has $X_b\%$ chance to remove a bleeding event, and $X_i\%$ chance to add an ischaemia event.")
st.write("If, however, ischaemia is also predicted, then a less aggressive intervention Y is made (e.g. no modification of therapy, but advice to the clinicians and patients that bleeding risk is high. It has chance $Y_b\%$ to remove a bleeding event, and $Y_i\%$ chance to add an ischaemia event.")
st.write("Set the efficacies of the interventions below:")

q_b = (
    st.slider(
        "$Q_b$",
        min_value=0.0,
        max_value=100.0,
        value=75.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
q_i = (
    st.slider(
        "$Q_i$",
        min_value=0.0,
        max_value=100.0,
        value=75.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
x_b = (
    st.slider(
        "$X_b$",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
x_i = (
    st.slider(
        "$X_i$",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
y_b = (
    st.slider(
        "$Y_b$",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)
y_i = (
    st.slider(
        "$Y_i$",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.1,
        format=f"%.2f%%",
    )
    / 100.0
)

# Probabilities of each outcome are worked out below. Note that
# X and Y can only reduce bleeding and increase ischaemia, which
# narrows the options for what can have led to a given outcome.
# In this deterministic model, if no intervention is performed,
# the outcome does not change.

# Previous NI/NB, correct no intervene
a_0 = q_b * p_b_ni_nb
# Previous NI/NB, incorrect X, bleeding already none, no increase in ischaemia
a_1 = q_i * (1 - q_b) * (1 - x_i) * p_b_ni_nb
# Previous NI/NB, incorrect Y, bleeding already none, no increase in ischaemia
a_2 = (1 - q_i) * (1 - q_b) * (1 - y_i) * p_b_ni_nb
# Previous NI/B, correct X, bleeding was removed, no increase in ischaemia
a_3 = q_i * q_b * x_b * (1 - x_i) * p_b_ni_b
# Previous NI/B, incorrect Y, bleeding was removed, no increase in ischaemia
a_4 = (1 - q_i) * q_b * y_b * (1 - y_i) * p_b_ni_b
# Add up all the terms
p_a_ni_nb = a_0 + a_1 + a_2 + a_3 + a_4

# Previous NI/B, incorrect no intervene
a_0 = (1 - q_b) * p_b_ni_b
# Previous NI/B, incorrect Y, no reduction in bleeding/increase in ischaemia
a_1 = (1 - q_i) * q_b * (1 - y_i) * (1 - y_b) * p_b_ni_b
# Previous NI/B, correct X, no reduction in bleeding/increase in ischaemia
a_2 = q_i * q_b * (1 - x_i) * (1 - x_b) * p_b_ni_b
# Add up all the terms
p_a_ni_b = a_0 + a_1 + a_2

# Previous I/NB, any action (nothing affects the outcome)
a_0 = p_b_i_nb
# Previous NI/NB, incorrect X, bleeding already none, increase in ischaemia
a_1 = q_i * (1 - q_b) * x_i * p_b_ni_nb
# Previous NI/NB, incorrect Y, bleeding already none, increase in ischaemia
a_2 = (1 - q_i) * (1 - q_b) * y_i * p_b_ni_nb
# Previous I/B, correct Y, ischaemia already present, reduces bleeding
a_3 = q_i * q_b * y_b * p_b_i_b
# Previous I/B, incorrect X, ischaemia already present, reduces bleeding
a_4 = (1 - q_i) * q_b * x_b * p_b_i_b
# Previous NI/B, incorrect Y, ischaemia added, reduces bleeding
a_5 = (1 - q_i) * q_b * y_i * x_b * p_b_ni_b
# Previous NI/B, correct X, ischaemia added, reduces bleeding
a_6 = q_i * q_b * x_i * x_b * p_b_ni_b
# Add up all the terms
p_a_i_nb = a_0 + a_1 + a_2 + a_3 + a_4 + a_5 + a_6

# Previous I/B, incorrect no intervene
a_0 = (1 - q_b) * p_b_i_b
# Previous I/B, correct Y, ischaemia already present, no reduction in bleeding
a_1 = q_i * q_b * (1 - y_b) * p_b_i_b
# Previous I/B, incorrect X, ischaemia already present, no reduction in bleeding
a_2 = (1 - q_i) * q_b * (1 - x_b) * p_b_i_b
# Previous NI/B, incorrect Y, ischaemia added, no reduction in bleeding
a_3 = (1 - q_i) * q_b * y_i * (1 - y_b) * p_b_ni_b
# Previous NI/B, correct X, ischaemia added, no reduction in bleeding
a_4 = q_i * q_b * x_i * (1 - x_b) * p_b_ni_b
# Add up all the terms
p_a_i_b = a_0 + a_1 + a_2 + a_3 + a_4

st.write("To make the outcome concretely interpretable in terms of numbers of patients, choose a number of patients $N$ who will undergo PCI and potentially receive a therapy intervention using the tool:")

n = (
    st.slider(
        "$N$",
        min_value=0,
        max_value=10000,
        value=5000,
    )
)

bleeding_before = int(n * (p_b_i_b + p_b_ni_b))
bleeding_after = int(n * (p_a_i_b + p_a_ni_b))
ischaemia_before = int(n * (p_b_i_b + p_b_i_nb))
ischaemia_after = int(n * (p_a_i_b + p_a_i_nb))

st.write("In this theoretical model, bleeding and ischaemia events are considered equally severe, so success is measured by counting the number of bleeding events reduced and comparing it in absolute terms to the number of ischaemia events added.")

st.write(f"**By using the tool on {n} patients, the expected changes in numbers of outcomes are as follows:**")

bleeding_increase = int(bleeding_after - bleeding_before)
st.write(f"**Bleeding: {bleeding_before} -> {bleeding_after} ({bleeding_increase:+d})**")

ischaemia_increase = ischaemia_after - ischaemia_before
st.write(f"**Ischaemia: {ischaemia_before} -> {ischaemia_after} ({ischaemia_increase:+d})**")

st.write("A benefit to using the tool is achieved if absolute numbers of bleeding events removed are not outweighed by ischaemia outcomes introduced. A positive number here means more bleeding was removed than ischaemia was added:")

trade_off = -bleeding_increase - ischaemia_increase
st.write(f"**Bleeding removed - ischaemia added: {trade_off:d}**")
