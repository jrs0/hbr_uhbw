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
# NI + NB: 92.2%
# I + NB: 6.6%
# NI + B: 1.0%
# I + B: 0.2%
#
# Success of the intervention used in group A is defined by
# a reduction in the rate of * + B outcomes, that comes with
# no increase in total I + * outcomes.

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import inputs
import utils
import roc

st.title("Deterministic Model")
st.write(
    "*Baseline patients are assumed to have determinsitic outcomes, which have a chance of being modified by the intervention.*"
)

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

# Get the user-input baseline prevalences (i.e. without performing interventions
# based on a bleeding/ischaemia risk model outcome)
defaults = {"ni_nb": 0.922, "ni_b": 0.01, "i_nb": 0.066}
p_observed = inputs.prevalences(baseline_container, defaults)

# Get the variables for convenience (the first "b" in the variable
# name means baseline, as opposed to "p_a_" (below) after the intervention
# has occurred.
p_b_ni_nb = p_observed.loc["No Ischaemia", "No Bleed"]
p_b_ni_b = p_observed.loc["No Ischaemia", "Bleed"]
p_b_i_nb = p_observed.loc["Ischaemia", "No Bleed"]
p_b_i_b = p_observed.loc["Ischaemia", "Bleed"]

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
# Note that splitting the interventions into X and Y in this model
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

# Print the model-accuracy input box and get the results
accuracy = inputs.model_accuracy()
q_b_tpr = accuracy["tpr_b"]
q_b_tnr = accuracy["tnr_b"]
q_i_tpr = accuracy["tpr_i"]
q_i_tnr = accuracy["tnr_i"]

# Show the required ROC curve to achieve this accuracy
roc.show_roc_expander(accuracy)

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

output_container.write(
    "In this theoretical model, bleeding and ischaemia events are considered equally severe, so success is measured by counting the number of bleeding events reduced and comparing it in absolute terms to the number of ischaemia events added."
)

output_container.write(
    f"**Expected changes in outcomes of a pool of {n} patients, compared to baseline**"
)

# In the sample size of n, scale the probabilities to obtain counts of
# patients having each outcome
bleeding_before = int(n * (p_b_i_b + p_b_ni_b))
ischaemia_before = int(n * (p_b_i_b + p_b_i_nb))
total_before = bleeding_before + ischaemia_before

# Calculate the outcomes as a result of the intervention
bleeding_after = int(n * (p_a_i_b + p_a_ni_b))
ischaemia_after = int(n * (p_a_i_b + p_a_i_nb))
total_after = bleeding_after + ischaemia_after

# Calculate the changes in outcomes
bleeding_increase = bleeding_after - bleeding_before
ischaemia_increase = ischaemia_after - ischaemia_before
total_increase = total_after - total_before

# Show the summary of outcome changes
col1, col2, col3 = output_container.columns(3)
col1.metric("Bleeding", bleeding_after, bleeding_increase, delta_color="inverse")
col2.metric("Ischaemia", ischaemia_after, ischaemia_increase, delta_color="inverse")
col3.metric(
    "Total Adverse Outcomes", total_after, total_increase, delta_color="inverse"
)
