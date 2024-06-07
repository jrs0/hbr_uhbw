import numpy as np
import scipy
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

import inputs
import utils
import roc

st.title("Discrete Risk Model")
st.write(
    "*Baseline patients are dichotomised into high and low risk groups, but all patients in the same group share the same risk (the risks do not follow a continuous distribution).*"
)

st.write(
    "This simulation uses the simplest possible non-deterministic model of patient outcomes, where all patients have one of two possible bleeding risks, and one of two possible ischaemia risks:"
)
st.write(
    "- **LIR vs. HIR**: All patients at HIR share the same risk of ischaemic outcomes, which is higher than the fixed, equal (among all patients) risk of ischaemia in the LIR group.\n- **LBR vs. HBR**: All patients in the HBR shared a common bleeding risk, which is higher than the fixed, equal risk to all LBR patients."
)

st.info(
    "In the model, being high risk for bleeding is independent of being high risk for ischaemia, and all outcome risks are also independent.",
    icon="ℹ️",
)

st.write(
    "Similarly to the deterministic model, baseline outcome prevalences are used as an input (**Input 1**). This information is paired with the proportions of patients at high bleeding risk and high ischaemia risk, which can be estimated from literature (**Input 2**). Together, this information determines the baseline patient risk in each risk group."
)

st.write(
    "In the model, a hypothetical risk-estimation tool attempts to decide which of the four risk categories a patient belongs to, with a certain degree of success (**Input 3**). An intervention is applied to the patients determined to be at high bleeding risk."
)

st.info(
    "The black-box model estimates bleeding and ischaemia risk category, and is specified by inputting true/false positive rates for correctly categorising patients.",
    icon="ℹ️",
)

st.write(
    "The intervention is assumed to modify the patient's bleeding and ischaemia risk. The intervention's effectiveness is specified as risk ratios relative to the patient's chance of adverse outcomes in their real risk category (**Input 4**)."
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

high_risk_container = st.container(border=True)
high_risk_container.header("Input 2: Number of Patients at High Risk", divider=True)
high_risk_container.write(
    "Input the proportion of patients who are at high risk of bleeding and/or ischaemia."
)
high_risk_container.write(
    "This value involves making a choice for what high risk means, and then inputting the proportion of patients that meet this high risk definition based on literature or experience."
)
high_risk_container.write(
    "The default value of 30% HBR follows from the estimated proportion of patients meeting the ARC HBR criteria, whereas the HIR default 50% is based on the estimate for the ESC/EACTS HIR definition."
)

p_b_hir = inputs.simple_prob(
    high_risk_container, "Proportion at high ischaemia risk (HIR) (%)", 50.0
)
p_b_hbr = inputs.simple_prob(
    high_risk_container, "Proportion at high bleeding risk (HBR) (%)", 30.0
)

risk_ratio_container = st.container(border=True)
risk_ratio_container.header("Input 3: Risk Ratios for High Risk Classes", divider=True)
risk_ratio_container.write(
    "Input the risk ratios between the high-risk class and the low-risk class for each outcome"
)
risk_ratio_container.write(
    "This value combines with the prevalence of the high risk category (Input 2) and the prevalence of actual outcomes (Input 1) to define the absolute risk of the high and low risk categories."
)

rr_hir = inputs.simple_positive(
    risk_ratio_container, "Risk ratio for HIR class compared to LIR", 1.5
)
rr_hbr = inputs.simple_positive(
    risk_ratio_container, "Risk ratio for HBR class compared to LBR", 1.5
)

# There are four unknowns in this simple model of underlying
# discrete bleeding/ischaemia risk. High/low bleeding/ischaemia
# risk categories are assumed to be independent, and we know
# the prevalence of those categories (they are an input). Assuming
# the risks are determined entirely by the bleeding/ischaemia risks
# in the low risk categories (two unknowns), and the relatives
# risks to get into the high risk categorY (another two unknowns),
# it is possible to solve the four nonlinear equations which come
# from knowing the overall outcome prevalence to calculate these
# unknowns.

def objective_fn(
    x: list[float],
    p_observed: pd.DataFrame,
    p_hir: float,
    p_hbr: float,
    rr_hir: float,
    rr_hbr: float,
) -> float:
    """Low/high bleeding risk objective

    Objective function to numerically find probabilities of
    combinations of outcomes in the low and high bleeding
    and ischaemia groups, by assuming independence of the
    inputted HIR and HBR risk ratios.

    Args:
        x: The unknown to be found by the optimisation
            procedure. The array contains these values:
            [x_ni_nb, x_ni_b, x_i_nb], which are
            the absolute risks of the outcome combinations
            in the LIR/LBR group. The final risk x_i_b is
            obtained by requiring that the items add up to
            1.
        p_observed: Observed prevalance of bleeding and ischaemia
            outcomes. Columns "No Bleed" and "Bleed", and index
            "No Ischaemia" and "Ischaemia"
        p_hir: Observed prevalence of high ischaemia risk
        p_hbr: Observed prevalence of high bleeding risk
        rr_hir: Risk ratio of HIR to LIR class
        rr_hbr: Risk ratio of HBR to LBR class

    Return:
        The L2 distance between the observed prevalences and the
            prevalences implied by the choice of x.
    """

    # Assuming the risk ratios for HIR and HBR act independently,
    # calculate what the absolute risks would be for patients in
    # other risk categories
    p_lir_lbr = utils.list_to_dataframe(x)
    p_lir_hbr = utils.scale_dependent_probs(p_lir_lbr, 1.0, rr_hbr)
    p_hir_lbr = utils.scale_dependent_probs(p_lir_lbr, rr_hir, 1.0)
    p_hir_hbr = utils.scale_dependent_probs(p_lir_lbr, rr_hir, rr_hbr)

    # Calculate the proportions of people in each category,
    # from the user inputs.
    w_lir_lbr = (1 - p_hir) * (1 - p_hbr)
    w_lir_hbr = (1 - p_hir) * p_hbr
    w_hir_lbr = p_hir * (1 - p_hbr)
    w_hir_hbr = p_hir * p_hbr

    # Weight the outcome probabilities according to the number
    # of people in each risk category
    a = w_lir_lbr * p_lir_lbr
    b = w_lir_hbr * p_lir_hbr
    c = w_hir_lbr * p_hir_lbr
    d = w_hir_hbr * p_hir_hbr
    new_outcomes = a + b + c + d

    # Perform a final check that the answer adds up to 1
    total = new_outcomes.sum().sum()
    if np.abs(total - 1.0) > 1e-5:
        raise RuntimeError(
            f"Calculated hypothetical prevalences must add to one; these add up to {100*total:.2f}%"
        )

    # Compare the calculated prevalences with the observed
    # prevalences and return the cost (L2 distance)
    return np.linalg.norm(p_observed.to_numpy() - new_outcomes.to_numpy())

# Set bounds on the probabilities which must be between
# zero and one (note that there are only three unknowns
# because the fourth is derived from the constraint that
# they add up to one.
bounds = scipy.optimize.Bounds([0, 0, 0], [1, 1, 1])

# Solve for the unknown low risk group probabilities and independent
# risk ratios by minimising the objective function
args = (p_observed, p_b_hir, p_b_hbr, rr_hir, rr_hbr)
initial_x = [0, 0, 0]
res = scipy.optimize.minimize(objective_fn, x0=initial_x, args=args, bounds=bounds)
x = res.x

# Check the solution is correct
cost = objective_fn(x, *args)
if cost > 1e-5:
    st.warning(f"Optimisation did not find an exact solution: cost = {cost}")

# Get the solved probabilities of outcomes in each of the 
# risk classes (the output from the optimisation above)
p_lir_lbr = utils.list_to_dataframe(x)
p_hir_lbr = utils.scale_dependent_probs(p_lir_lbr, rr_hir, 1.0)
p_lir_hbr = utils.scale_dependent_probs(p_lir_lbr, 1.0, rr_hbr)
p_hir_hbr = utils.scale_dependent_probs(p_lir_lbr, rr_hir, rr_hbr)

# Calculate the proportions of people in each category,
# from the user inputs.
w_lir_lbr = (1 - p_b_hir) * (1 - p_b_hbr)
w_lir_hbr = (1 - p_b_hir) * p_b_hbr
w_hir_lbr = p_b_hir * (1 - p_b_hbr)
w_hir_hbr = p_b_hir * p_b_hbr

baseline_risks = st.container(border=True)
baseline_risks.header("Output 1: Model of Baseline Risk", divider="blue")
baseline_risks.write(
    "This section shows the underlying probability model that patients are assumed to follow in the analysis below."
)
baseline_risks.write(
    "Patients are in one of four risk groups, depending on the proportions entered in **Input 2**. The differences in risk between the high and low risk groups are controlled by **Input 3**."
)
baseline_risks.write(
    "The weighted average of the four groups results in the observed prevalences of **Input 1**."   
)

baseline_col_1, baseline_col_2 = baseline_risks.columns(2)

# LIR/LBR
baseline_col_1.subheader(
    f"LIR/LBR ({100 * w_lir_lbr:.2f}%)",
    divider="green",
)
baseline_col_1.write(
    "Absolute risk for patients at low risk for both outcomes."
)
baseline_col_1.write((100*p_lir_lbr).style.format("{:.2f}%"))

# HIR/LBR
baseline_col_1.subheader(
    f"HIR/LBR ({100 * w_hir_lbr:.2f}%)",
    divider="orange",
)
baseline_col_1.write(
    "Absolute risk for patients at high ischaemia risk but low bleeding risk"
)
baseline_col_1.write((100*p_hir_lbr).style.format("{:.2f}%"))

# LIR/HBR
baseline_col_2.subheader(
    f"LIR/HBR ({100 * w_lir_hbr:.2f}%)",
    divider="orange",
)
baseline_col_2.write(
    "Absolute risk for patients at high bleeding risk but low ischaemia risk."
)
baseline_col_2.write((100*p_lir_hbr).style.format("{:.2f}%"))

# HIR/HBR
baseline_col_2.subheader(
    f"HIR/HBR ({100 * w_hir_hbr:.2f}%)",
    divider="red",
)
baseline_col_2.write(
    "Absolute risk for patients at high risk for both outcomes."
)
baseline_col_2.write((100*p_hir_hbr).style.format("{:.2f}%"))

# Print the model-accuracy input box and get the results
accuracy = inputs.model_accuracy()
q_b_tpr = accuracy["tpr_b"]
q_b_tnr = accuracy["tnr_b"]
q_i_tpr = accuracy["tpr_i"]
q_i_tnr = accuracy["tnr_i"]

# Show the required ROC curve to achieve this accuracy
roc.show_roc_expander(accuracy)

intervention = st.container(border=True)
intervention.header("Input 3: Intervention Effectiveness", divider=True)
intervention.write(
    "In this model, an intervention is applied to patients assessed by the black-box model to be high bleeding risk but low ischaemia risk. This intervention could, for example, reduce the strength or duration of DAPT therapy."
)
intervention.write(
    "The effectiveness of the intervention depends on the patient's real risk category. This risk-dependent effectiveness is input here as risk ratios for each outcome."
)
intervention.write(
    "The default numbers provided correspond to an intervention which only decreases bleeding in HBR patients, and only increases ischaemia in HIR patients."
)

intervention_col_1, intervention_col_2 = intervention.columns(2)

# LIR/LBR
intervention_col_1.subheader(
    "Effect on LIR/LBR Patients",
    divider="green",
)
intervention_col_1.write(
    "What effect does the intervention have on patients with low risk for both bleeding and ischaemia?"
)
rr_int_i_lir_lbr = inputs.simple_positive(
    intervention_col_1, "Ischaemia risk ratio", 1.0, key="rr_int_i_lir_lbr"
)
rr_int_b_lir_lbr = inputs.simple_positive(
    intervention_col_1, "Bleeding risk ratio", 1.0, key="rr_int_b_lir_lbr"
)

# HIR/LBR
intervention_col_1.subheader(
    "Effect on HIR/LBR Patients",
    divider="orange",
)
intervention_col_1.write(
    "What effect does the intervention have on patients with high ischaemia risk but low bleeding risk?"
)
rr_int_i_hir_lbr = inputs.simple_positive(
    intervention_col_1, "Ischaemia risk ratio", 1.2, key="rr_int_i_hir_lbr"
)
rr_int_b_hir_lbr = inputs.simple_positive(
    intervention_col_1, "Bleeding risk ratio", 1.0, key="rr_int_b_hir_lbr"
)

# LIR/HBR
intervention_col_2.subheader(
    "Effect on LIR/HBR Patients",
    divider="orange",
)
intervention_col_2.write(
    "What effect does the intervention have on patients with high bleeding risk but low ischaemia risk?"
)
rr_int_i_lir_hbr = inputs.simple_positive(
    intervention_col_2, "Ischaemia risk ratio", 1.0, key="rr_int_i_lir_hbr"
)
rr_int_b_lir_hbr = inputs.simple_positive(
    intervention_col_2, "Bleeding risk ratio", 0.8, key="rr_int_b_lir_hbr"
)

# HIR/HBR
intervention_col_2.subheader(
    "Effect on HIR/HBR Patients",
    divider="red",
)
intervention_col_2.write(
    "What effect does the intervention have on patients with high risk for both bleeding and ischaemia?"
)
rr_int_i_hir_hbr = inputs.simple_positive(
    intervention_col_2, "Ischaemia risk ratio", 1.2, key="rr_int_i_hir_hbr"
)
rr_int_b_hir_hbr = inputs.simple_positive(
    intervention_col_2, "Bleeding risk ratio", 0.8, key="rr_int_b_hir_hbr"
)

# Calculate the result of making a risk estimate using the black box and then performing
# an intervention based on the result. The calculation is an average over the following
# possibilities:
#
# 1) A patient has some original (baseline) "true" risk category, according to the 
#    probabilities shown in the "Outcome 1" box. This defines the baseline absolute
#    outcome risks for the patient.
# 2) An estimate is made for this true baseline risk category using the black box.
#    The result is an "estimated" risk category, which is one of four possibilities.
#    This leads to performing an intervention if the category is estimated to be
#    LIR/HBR. For all other estimates, no intervention is applied.
# 3) The intervention makes one of four possible modifications to the outcome 
#    probability, depending on the patient's true risk category.

# The first step is to find the probability of performing an intervention, which is
# the only mechanism for modifying a patient's baseline risk. This is equal to the
# chance of estimating a LIR/HBR category over all possible real risk categories.
# In the calculations below, remember that the true positive/negative rates are
# conditioned on the patient being truly positive or negative (high risk or low
# risk).

# Probability of intervention (estimate LIR/HBR) given real category is LIR/LBR
p_int_lir_lbr = q_i_tnr * (1 - q_b_tnr)
p_no_int_lir_lbr = 1 - p_int_lir_lbr

# Probability of intervention (estimate LIR/HBR) given real category is LIR/HBR
p_int_lir_hbr = q_i_tnr * q_b_tpr
p_no_int_lir_hbr = 1 - p_int_lir_hbr

# Probability of intervention (estimate LIR/HBR) given real category is HIR/LBR
p_int_hir_lbr = (1 - q_i_tpr) * (1 - q_b_tnr)
p_no_int_hir_lbr = 1 - p_int_hir_lbr

# Probability of intervention (estimate LIR/HBR) given real category is HIR/HBR
p_int_hir_hbr = (1 - q_i_tpr) * q_b_tpr
p_no_int_hir_hbr = 1 - p_int_hir_hbr

# Get intervention probability by weighting according to the prevalence of the
# true risk categories
a = w_lir_lbr * p_int_lir_lbr
b = w_lir_hbr * p_int_lir_hbr
c = w_hir_lbr * p_int_hir_lbr
d = w_hir_hbr * p_int_hir_hbr
p_int = a + b + c + d

# Also calculate the probability of no intervention and check
# that the sum is one
a = w_lir_lbr * p_no_int_lir_lbr
b = w_lir_hbr * p_no_int_lir_hbr
c = w_hir_lbr * p_no_int_hir_lbr
d = w_hir_hbr * p_no_int_hir_hbr
p_no_int = a + b + c + d

if np.abs((p_int + p_no_int) - 1.0) > 1e-7:
    raise RuntimeError(f"P(int) + P(no int) != 1 (instead {p_int + p_no_int})")

# Within the intervention group, the risk of each outcome is modified differently,
# as below. In each case, starting with the outcome risks for a patient in that class,
# the risk is modified by the risk ratios specified for the intervention effects in
# that class. (Note this calculation is probabilities given that an intervention occurred)
# The structure of this calculation is:
#
# P(outcomes | intervention) = P(outcomes | A)P(A), 
#
# where A is a "true" risk category, and P(outcomes) is the risks for patients in
# category A after being modified by the intervention.
a = utils.scale_dependent_probs(p_lir_lbr, rr_int_i_lir_lbr, rr_int_b_lir_lbr) * w_lir_lbr
b = utils.scale_dependent_probs(p_lir_hbr, rr_int_i_lir_hbr, rr_int_b_lir_hbr) * w_lir_hbr
c = utils.scale_dependent_probs(p_hir_lbr, rr_int_i_hir_lbr, rr_int_b_hir_lbr) * w_hir_lbr
d = utils.scale_dependent_probs(p_hir_hbr, rr_int_i_hir_hbr, rr_int_b_hir_hbr) * w_hir_hbr
p_int_outcomes = a + b + c + d

# Within the no-intervention group, calculate the expected outcome probabilities.
a = p_lir_lbr * w_lir_lbr
b = p_lir_hbr * w_lir_hbr
c = p_hir_lbr * w_hir_lbr
d = p_hir_hbr * w_hir_hbr
p_no_int_outcomes = a + b + c + d

# This is the same as the following formula, but the reason is not simply that
# "these are the background outcome prevalences with no intervention" -- the reason
# is that a model could exist which has no bleeding in the "non-intervention group"
# (i.e. if it could predict the future). The reason for this equality is more 
# something like the models risk estimates are independent of the outcomes in each
# risk category.
#p_no_int_outcomes = x_to_dataframe([p_b_ni_nb, p_b_ni_b, p_b_i_nb])

# Calculate overall new outcomes
p_new_outcomes = p_int * p_int_outcomes + p_no_int * p_no_int_outcomes

# Do a sanity check
total_prob = p_new_outcomes.sum().sum()
if np.abs(total_prob - 1.0) > 1e-7:
    raise RuntimeError(f"Invalid total probability {total_prob} in output prevalence")

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
bleeding_before = int(n * p_observed["Bleed"].sum())
ischaemia_before = int(n * p_observed.loc["Ischaemia"].sum())
total_before = bleeding_before + ischaemia_before

# Calculate the outcomes as a result of the intervention
bleeding_after = int(n * p_new_outcomes["Bleed"].sum())
ischaemia_after = int(n * p_new_outcomes.loc["Ischaemia"].sum())
total_after = bleeding_after + ischaemia_after

# Calculate the changes in outcomes
bleeding_increase = bleeding_after - bleeding_before
ischaemia_increase = ischaemia_after - ischaemia_before
total_increase = total_after - total_before

# Show the summary of outcome changes
col1, col2, col3 = output_container.columns(3)
col1.metric("Bleeding", bleeding_after, bleeding_increase, delta_color="inverse")
col2.metric("Ischaemia", ischaemia_after, ischaemia_increase, delta_color="inverse")
col3.metric("Total Adverse Outcomes", total_after, total_increase, delta_color="inverse")




