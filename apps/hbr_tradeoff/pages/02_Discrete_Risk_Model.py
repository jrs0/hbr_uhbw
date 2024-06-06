import numpy as np
import scipy
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


from inputs import input_prevalences
from utils import simple_prob_input, simple_positive_input

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
baseline_prevalences = input_prevalences(baseline_container, defaults)

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

p_b_hir = simple_prob_input(
    high_risk_container, "Proportion at high ischaemia risk (HIR) (%)", 50.0
)
p_b_hbr = simple_prob_input(
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

rr_hir = simple_positive_input(
    risk_ratio_container, "Risk ratio for HIR class compared to LIR", 1.5
)
rr_hbr = simple_positive_input(
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


def get_p_lir_hbr(p_lir_lbr: pd.DataFrame, rr_hbr: float) -> pd.DataFrame:
    """Get the probabilities of outcomes in the LIR/HBR group

    Args:
        p_lir_lbr: The matrix of LIR/LBR probabilities.
        rr_hbr: The relative risk of the high bleeding risk group

    Raises:
        RuntimeError if probabilities do not add up to one.

    Returns:
        A dataframe containing the probabilities of ischaemia
            as the index and bleeding as the columns.
    """

    p_ni_nb_lir_lbr = p_lir_lbr.loc["No Ischaemia", "No Bleed"]
    p_ni_b_lir_lbr = p_lir_lbr.loc["No Ischaemia", "Bleed"]
    p_i_nb_lir_lbr = p_lir_lbr.loc["Ischaemia", "No Bleed"]
    p_i_b_lir_lbr = p_lir_lbr.loc["Ischaemia", "Bleed"]

    # For a patient in the HBR group (but the LIR group), the
    # chance of a bleed is higher by the HBR risk ratio. The
    # chance of no bleed is obtained by assuming the total
    # proportion of ischaemia outcomes has not changed (since
    # patients are still LIR).
    p_ni_b_lir_hbr = rr_hbr * p_ni_b_lir_lbr
    p_ni_lir_lbr = p_ni_nb_lir_lbr + p_ni_b_lir_lbr  # previous P(no ischaemia)
    p_ni_nb_lir_hbr = p_ni_lir_lbr - p_ni_b_lir_hbr

    # Do the same calculation for the chance of an ischaemia
    # outcome (probability unaffected) for a patient in the HBR group.
    p_i_b_lir_hbr = rr_hbr * p_i_b_lir_lbr
    p_i_lir_lbr = p_i_nb_lir_lbr + p_i_b_lir_lbr  # previous P(ischaemia)
    p_i_nb_lir_hbr = p_i_lir_lbr - p_i_b_lir_hbr

    # Before moving on, check that the absolute outcome risks
    # in the LIR/HBR group add up to 1
    p = p_ni_nb_lir_hbr + p_ni_b_lir_hbr + p_i_nb_lir_hbr + p_i_b_lir_hbr
    if np.abs(p - 1.0) > 1e-5:
        raise RuntimeError(
            f"Total proportions in LIR/HBR group must add to one; these add up to {100*p:.2f}%"
        )

    data = {
        "No Bleed": [p_ni_nb_lir_hbr, p_i_nb_lir_hbr],
        "Bleed": [p_ni_b_lir_hbr, p_i_b_lir_hbr],
    }
    return pd.DataFrame(data, index=["No Ischaemia", "Ischaemia"])


def get_p_hir_lbr(p_lir_lbr: pd.DataFrame, rr_hir: float) -> pd.DataFrame:
    """Get the probabilities of outcomes in the HIR/LBR group

    Args:
        p_lir_lbr: The matrix of LIR/LBR probabilities.
        rr_hir: The relative risk of the high ischaemia risk group

    Raises:
        RuntimeError if probabilities do not add up to one.

    Returns:
        A dataframe containing the probabilities of ischaemia
            as the index and bleeding as the columns.
    """

    p_ni_nb_lir_lbr = p_lir_lbr.loc["No Ischaemia", "No Bleed"]
    p_ni_b_lir_lbr = p_lir_lbr.loc["No Ischaemia", "Bleed"]
    p_i_nb_lir_lbr = p_lir_lbr.loc["Ischaemia", "No Bleed"]
    p_i_b_lir_lbr = p_lir_lbr.loc["Ischaemia", "Bleed"]

    # Now, repeat these two calculations for patients at HIR
    # but not HBR. This time, chance of ischaemia shifts
    # upwards by the HIR risk ratio, but overall bleeding rate
    # remains the same.
    p_i_nb_hir_lbr = rr_hir * p_i_nb_lir_lbr
    p_nb_lir_lbr = p_ni_nb_lir_lbr + p_i_nb_lir_lbr  # previous P(no bleed)
    p_ni_nb_hir_lbr = p_nb_lir_lbr - p_i_nb_hir_lbr

    # Repeat for the chance of a bleeding outcome (probability
    # unaffected
    p_i_b_hir_lbr = rr_hir * p_i_b_lir_lbr
    p_b_lir_lbr = p_ni_b_lir_lbr + p_i_b_lir_lbr  # previous P(bleed)
    p_ni_b_hir_lbr = p_b_lir_lbr - p_i_b_hir_lbr

    # Check that the absolute outcome risks
    # in the HIR/LBR group add up to 1
    p = p_ni_nb_hir_lbr + p_ni_b_hir_lbr + p_i_nb_hir_lbr + p_i_b_hir_lbr
    if np.abs(p - 1.0) > 1e-5:
        raise RuntimeError(
            f"Total proportions in HIR/LBR group must add to one; these add up to {100*p:.2f}%"
        )

    data = {
        "No Bleed": [p_ni_nb_hir_lbr, p_i_nb_hir_lbr],
        "Bleed": [p_ni_b_hir_lbr, p_i_b_hir_lbr],
    }
    return pd.DataFrame(data, index=["No Ischaemia", "Ischaemia"])


def get_p_hir_hbr(
    p_lir_lbr: pd.DataFrame, rr_hir: float, rr_hbr: float
) -> pd.DataFrame:
    """Get the probabilities of outcomes in the HIR/HBR group

    Args:
        p_lir_lbr: The matrix of LIR/LBR probabilities.
        rr_hir: The relative risk of the high ischaemia risk group
        rr_hbr: The relative risk of the high bleeding risk group

    Raises:
        RuntimeError if probabilities do not add up to one.

    Returns:
        A dataframe containing the probabilities of ischaemia
            as the index and bleeding as the columns.
    """

    p_ni_nb_lir_lbr = p_lir_lbr.loc["No Ischaemia", "No Bleed"]
    p_ni_b_lir_lbr = p_lir_lbr.loc["No Ischaemia", "Bleed"]
    p_i_nb_lir_lbr = p_lir_lbr.loc["Ischaemia", "No Bleed"]
    p_i_b_lir_lbr = p_lir_lbr.loc["Ischaemia", "Bleed"]

    # The final set of calculations is for patients at both
    # HBR and HIR. This time, the independence of risk ratios
    # assumptions is used to say that:
    p_i_b_hir_hbr = rr_hir * rr_hbr * p_i_b_lir_lbr

    # This time, the marginals (probability of total ischaemia
    # and total bleeding) are assumed to scale with the individual
    # risk ratios. First, for total ischaemia probability:
    p_i_lir_lbr = p_i_nb_lir_lbr + p_i_b_lir_lbr  # previous P(ischaemia)
    p_i_hir_hbr = rr_hir * p_i_lir_lbr
    p_i_nb_hir_hbr = p_i_hir_hbr - p_i_b_hir_hbr

    # And for the total bleeding marginal in the HBR/HIR group
    p_b_lir_lbr = p_ni_b_lir_lbr + p_i_b_lir_lbr  # previous P(bleed)
    p_b_hir_hbr = rr_hbr * p_b_lir_lbr
    p_ni_b_hir_hbr = p_b_hir_hbr - p_i_b_hir_hbr

    # Finally, the chance of neither event is obtained by requiring
    # all the probabilities to add up to 1.
    p_ni_nb_hir_hbr = 1 - p_ni_b_hir_hbr - p_i_nb_hir_hbr - p_i_b_hir_hbr

    # No need to check sum to one here because they do by construction
    # of the previous line.

    data = {
        "No Bleed": [p_ni_nb_hir_hbr, p_i_nb_hir_hbr],
        "Bleed": [p_ni_b_hir_hbr, p_i_b_hir_hbr],
    }
    return pd.DataFrame(data, index=["No Ischaemia", "Ischaemia"])


def x_to_dataframe(x: list[float]) -> pd.DataFrame:
    """Convert the optimisation parameter to a dataframe

    Args:
        x: The optimisation parameter containing the LIR/LBR
            probabilities. The array contains these values:
            [x_ni_nb, x_ni_b, x_i_nb], which are
            the absolute risks of the outcome combinations
            in the LIR/LBR group. The final risk x_i_b is
            obtained by requiring that the items add up to
            1.

    Returns:
        A table of outcome probabilities containing ischaemia
            outcome as index and bleeding outcome as column.
    """
    # Unpack all the unknowns (these are the absolute risks
    # for a patient in the LIR/LBR group)
    p_ni_nb_lir_lbr = x[0]
    p_ni_b_lir_lbr = x[1]
    p_i_nb_lir_lbr = x[2]
    p_i_b_lir_lbr = 1 - x[0] - x[1] - x[2]

    data = {
        "No Bleed": [p_ni_nb_lir_lbr, p_i_nb_lir_lbr],
        "Bleed": [p_ni_b_lir_lbr, p_i_b_lir_lbr],
    }
    return pd.DataFrame(data, index=["No Ischaemia", "Ischaemia"])


def objective_fn(
    x: list[float],
    p_ni_nb: float,
    p_ni_b: float,
    p_i_nb: float,
    p_i_b: float,
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
        p_ni_nb: Observed no ischaemia/no bleeding prevalence
        p_ni_b: Observed no ischaemia but bleeding prevalence
        p_i_nb: Observed ischaemia but no bleeding prevalence
        p_i_b: Observed ischaemia and bleeding prevalence
        p_hir: Observed prevalence of high ischaemia risk
        p_hbr: Observed prevalence of high bleeding risk
        rr_hir: Risk ratio of HIR to LIR class
        rr_hbr: Risk ratio of HBR to LBR class

    Return:
        The L2 distance between the observed prevalences and the
            prevalences implied by the choice of x.
    """

    p_lir_lbr = x_to_dataframe(x)

    # Assuming the risk ratios for HIR and HBR act independently,
    # calculate what the absolute risks would be for patients in
    # other risk categories

    p_lir_hbr = get_p_lir_hbr(p_lir_lbr, rr_hbr)
    p_hir_lbr = get_p_hir_lbr(p_lir_lbr, rr_hir)
    p_hir_hbr = get_p_hir_hbr(p_lir_lbr, rr_hir, rr_hbr)

    # Calculate what the observed prevalences would
    # be if x were correct -- the absolute risks in each
    # category are scaled by the prevalence of that category
    w_lir_lbr = (1 - p_hir) * (1 - p_hbr)
    w_lir_hbr = (1 - p_hir) * p_hbr
    w_hir_lbr = p_hir * (1 - p_hbr)
    w_hir_hbr = p_hir * p_hbr

    # Weight the classes to obtain the overall outcomes
    a = w_lir_lbr * p_lir_lbr
    b = w_lir_hbr * p_lir_hbr
    c = w_hir_lbr * p_hir_lbr
    d = w_hir_hbr * p_hir_hbr
    p_outcomes = a + b + c + d

    # Perform a final check that the answer adds up to 1
    a = p_outcomes.loc["No Ischaemia", "No Bleed"]
    b = p_outcomes.loc["No Ischaemia", "Bleed"]
    c = p_outcomes.loc["Ischaemia", "No Bleed"]
    d = p_outcomes.loc["Ischaemia", "Bleed"]
    p = a + b + c + d
    if np.abs(p - 1.0) > 1e-5:
        raise RuntimeError(
            f"Calculated hypothetical prevalences must add to one; these add up to {100*p:.2f}%"
        )

    # Compare the calculated prevalences with the observed
    # prevalences and return the cost (L2 distance)
    w = (a - p_ni_nb) ** 2
    x = (b - p_ni_b) ** 2
    y = (c - p_i_nb) ** 2
    z = (d - p_i_b) ** 2
    return w + x + y + z


# Set bounds on the probabilities which must be between
# zero and one (note that there are only three unknowns
# because the fourth is derived from the constraint that
# they add up to one.
bounds = scipy.optimize.Bounds([0, 0, 0], [1, 1, 1])

# Solve for the unknown low risk group probabilities and independent
# risk ratios by minimising the objective function
args = (p_b_ni_nb, p_b_ni_b, p_b_i_nb, p_b_i_b, p_b_hir, p_b_hbr, rr_hir, rr_hbr)
initial_x = 3 * [0]
res = scipy.optimize.minimize(objective_fn, x0=initial_x, args=args, bounds=bounds)
x = res.x

# Check the solution is correct
cost = objective_fn(x, *args)

# Solved probabilities of bleeding/ischaemia in LBR/LIR groups
p_lir_lbr = x_to_dataframe(x)

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
p_class_lir_lbr = (1 - p_b_hir) * (1 - p_b_hbr)
baseline_col_1.subheader(
    f"LIR/LBR ({100 * p_class_lir_lbr:.2f}%)",
    divider="green",
)
baseline_col_1.write(
    "Absolute risk for patients at low risk for both outcomes."
)
baseline_col_1.write((100*p_lir_lbr).style.format("{:.2f}%"))

# HIR/LBR
p_class_hir_lbr = p_b_hir * (1 - p_b_hbr)
p_hir_lbr = get_p_hir_lbr(p_lir_lbr, rr_hir)
baseline_col_1.subheader(
    f"HIR/LBR ({100 * p_class_hir_lbr:.2f}%)",
    divider="orange",
)
baseline_col_1.write(
    "Absolute risk for patients at high ischaemia risk but low bleeding risk"
)
baseline_col_1.write((100*p_hir_lbr).style.format("{:.2f}%"))

# LIR/HBR
p_class_lir_hbr = (1 - p_b_hir) * p_b_hbr
p_lir_hbr = get_p_lir_hbr(p_lir_lbr, rr_hbr)
baseline_col_2.subheader(
    f"LIR/HBR ({100 * p_class_lir_hbr:.2f}%)",
    divider="orange",
)
baseline_col_2.write(
    "Absolute risk for patients at high bleeding risk but low ischaemia risk."
)
baseline_col_2.write((100*p_lir_hbr).style.format("{:.2f}%"))

# HIR/HBR
p_class_hir_hbr = p_b_hir * p_b_hbr
p_hir_hbr = get_p_hir_hbr(p_lir_lbr, rr_hir, rr_hbr)
baseline_col_2.subheader(
    f"HIR/HBR ({100 * p_class_hir_hbr:.2f}%)",
    divider="red",
)
baseline_col_2.write(
    "Absolute risk for patients at high risk for both outcomes."
)
baseline_col_2.write((100*p_hir_hbr).style.format("{:.2f}%"))

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
rr_int_i_lir_lbr = simple_positive_input(
    intervention_col_1, "Ischaemia risk ratio", 1.0, key="rr_int_i_lir_lbr"
)
rr_int_b_lir_lbr = simple_positive_input(
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
rr_int_i_hir_lbr = simple_positive_input(
    intervention_col_1, "Ischaemia risk ratio", 1.2, key="rr_int_i_hir_lbr"
)
rr_int_b_hir_lbr = simple_positive_input(
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
rr_int_i_lir_hbr = simple_positive_input(
    intervention_col_2, "Ischaemia risk ratio", 1.0, key="rr_int_i_lir_hbr"
)
rr_int_b_lir_hbr = simple_positive_input(
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
rr_int_i_hir_hbr = simple_positive_input(
    intervention_col_2, "Ischaemia risk ratio", 1.2, key="rr_int_i_hir_hbr"
)
rr_int_b_hir_hbr = simple_positive_input(
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
a = p_class_lir_lbr * p_int_lir_lbr
b = p_class_lir_hbr * p_int_lir_hbr
c = p_class_hir_lbr * p_int_hir_lbr
d = p_class_hir_hbr * p_int_hir_hbr
p_int = a + b + c + d

# Also calculate the probability of no intervention and check
# that the sum is one
a = p_class_lir_lbr * p_no_int_lir_lbr
b = p_class_lir_hbr * p_no_int_lir_hbr
c = p_class_hir_lbr * p_no_int_hir_lbr
d = p_class_hir_hbr * p_no_int_hir_hbr
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
a = get_p_hir_hbr(p_lir_lbr, rr_int_i_lir_lbr, rr_int_b_lir_lbr) * p_class_lir_lbr
b = get_p_hir_hbr(p_lir_hbr, rr_int_i_lir_hbr, rr_int_b_lir_hbr) * p_class_lir_hbr
c = get_p_hir_hbr(p_hir_lbr, rr_int_i_hir_lbr, rr_int_b_hir_lbr) * p_class_hir_lbr
d = get_p_hir_hbr(p_hir_hbr, rr_int_i_hir_hbr, rr_int_b_hir_hbr) * p_class_hir_hbr
p_int_outcomes = a + b + c + d

# Within the no-intervention group, calculate the expected outcome probabilities.
a = p_lir_lbr * p_class_lir_lbr
b = p_lir_hbr * p_class_lir_hbr
c = p_hir_lbr * p_class_hir_lbr
d = p_hir_hbr * p_class_hir_hbr
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

bleeding_before = int(n * (p_b_i_b + p_b_ni_b))
bleeding_after = int(n * p_new_outcomes["Bleed"].sum())
ischaemia_before = int(n * (p_b_i_b + p_b_i_nb))
ischaemia_after = int(n * p_new_outcomes.loc["Ischaemia"].sum())

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




