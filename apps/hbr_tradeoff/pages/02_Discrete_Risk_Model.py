import numpy as np
import scipy
import pandas as pd
import streamlit as st

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


p_b_ni_nb = simple_prob_input(
    baseline_container, "Proportion with no ischaemia and no bleeding (%)", 80.0
)
p_b_i_nb = simple_prob_input(
    baseline_container, "Proportion with ischaemia but no bleeding (%)", 18.0
)
p_b_ni_b = simple_prob_input(
    baseline_container, "Proportion with bleeding but no ischaemia (%)", 1.0
)
p_b_i_b = simple_prob_input(
    baseline_container, "Proportion with bleeding and ischaemia (%)", 1.0
)

total_prob = p_b_ni_nb + p_b_ni_b + p_b_i_nb + p_b_i_b
if np.abs(total_prob - 1.0) > 1e-5:
    st.error(
        f"Total proportions must add up to 100%; these add up to {100*total_prob:.2f}%"
    )

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
risk_ratio_container.header("Input 3: Risk Ratios for high risk classes", divider=True)
risk_ratio_container.write(
    "Input the risk ratios between the high-risk class and the low-risk class for each outcome"
)
risk_ratio_container.write(
    "This value combines with the prevalence of the high risk category (Input 2) and the prevalence of actual outcomes (Input 1) to define the absolute risk of the high and low risk categories."
)
risk_ratio_container.write(
    "The default value of 30% HBR follows from the estimated proportion of patients meeting the ARC HBR criteria, whereas the HIR default 50% is based on the estimate for the ESC/EACTS HIR definition."
)

rr_hir = simple_prob_input(
    risk_ratio_container, "Risk ratio for HIR class compared to LIR", 1.1
)
rr_hbr = simple_prob_input(
    risk_ratio_container, "Risk ratio for HBR class compared to LBR", 1.2
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

    # Unpack all the unknowns (these are the absolute risks
    # for a patient in the LIR/LBR group)
    p_ni_nb_lir_lbr = x[0]
    p_ni_b_lir_lbr = x[1]
    p_i_nb_lir_lbr = x[2]
    p_i_b_lir_lbr = 1 - x[0] - x[1] - x[2]

    # Assuming the risk ratios for HIR and HBR act independently,
    # calculate what the absolute risks would be for patients in
    # other risk categories

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

    # The final set of calculations is for patients at both
    # HBR and HIR. This time, the independence of risk ratios
    # assumptions is used to say that:
    p_i_b_hir_hbr = rr_hir * rr_hbr * p_i_b_lir_lbr

    # This time, the marginals (probability of total ischaemia
    # and total bleeding) are assumed to scale with the individual
    # risk ratios. First, for total ischaemia probability:
    p_i_hir_hbr = rr_hir * p_i_lir_lbr
    p_i_nb_hir_hbr = p_i_hir_hbr - p_i_b_hir_hbr

    # And for the total bleeding marginal in the HBR/HIR group
    p_b_hir_hbr = rr_hbr * p_b_lir_lbr
    p_ni_b_hir_hbr = p_b_hir_hbr - p_i_b_hir_hbr

    # Finally, the chance of neither event is obtained by requiring
    # all the probabilities to add up to 1.
    p_ni_nb_hir_hbr = 1 - p_ni_b_hir_hbr - p_i_nb_hir_hbr - p_i_b_hir_hbr

    # No need to check sum to one here because they do by construction
    # of the previous line.

    # Calculate what the observed prevalences would
    # be if x were correct -- the absolute risks in each
    # category are scaled by the prevalence of that category
    p_lir_lbr = (1 - p_hir) * (1 - p_hbr)
    p_lir_hbr = (1 - p_hir) * p_hbr
    p_hir_lbr = p_hir * (1 - p_hbr)
    p_hir_hbr = p_hir * p_hbr
    
    # No ischaemia/no bleeding outcomes
    a = p_ni_nb_lir_lbr * p_lir_lbr
    b = p_ni_nb_lir_hbr * p_lir_hbr
    c = p_ni_nb_hir_lbr * p_hir_lbr
    d = p_ni_nb_hir_hbr * p_hir_hbr
    p_x_ni_nb = a + b + c + d
    
    # No ischaemia/bleeding
    a = p_ni_b_lir_lbr * p_lir_lbr
    b = p_ni_b_lir_hbr * p_lir_hbr
    c = p_ni_b_hir_lbr * p_hir_lbr
    d = p_ni_b_hir_hbr * p_hir_hbr
    p_x_ni_b = a + b + c + d 
    
    # Ischaemia/no bleeding
    a = p_i_nb_lir_lbr * p_lir_lbr
    b = p_i_nb_lir_hbr * p_lir_hbr
    c = p_i_nb_hir_lbr * p_hir_lbr
    d = p_i_nb_hir_hbr * p_hir_hbr
    p_x_i_nb = a + b + c + d 

    # Ischaemia/bleeding
    a = p_i_b_lir_lbr * p_lir_lbr
    b = p_i_b_lir_hbr * p_lir_hbr
    c = p_i_b_hir_lbr * p_hir_lbr
    d = p_i_b_hir_hbr * p_hir_hbr
    p_x_i_b = a + b + c + d 

    # Perform a final check that the answer adds up to 1
    p = p_x_ni_nb + p_x_ni_b + p_x_i_nb + p_x_i_b
    if np.abs(p - 1.0) > 1e-5:
        raise RuntimeError(
            f"Calculated hypothetical prevalences must add to one; these add up to {100*p:.2f}%"
        )    

    # Compare the calculated prevalences with the observed
    # prevalences and return the cost (L2 distance)
    a = (p_x_ni_nb - p_ni_nb) ** 2
    b = (p_x_ni_b - p_ni_b) ** 2
    c = (p_x_i_nb - p_i_nb) ** 2
    d = (p_x_i_b - p_i_b) ** 2
    return a + b + c + d


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
p_ni_nb_lir_lbr = x[0]
p_ni_b_lir_lbr = x[1]
p_i_nb_lir_lbr = x[2]
p_i_b_lir_lbr = 1 - x[0] - x[1] - x[2]

st.write(f"Cost = {cost}")
st.write(f"p_ni_nb_lir = {p_ni_nb_lir_lbr}")
st.write(f"p_ni_b_lir = {p_ni_b_lir_lbr}")
st.write(f"p_i_nb_lir = {p_i_nb_lir_lbr}")
st.write(f"p_i_b_lir = {p_i_b_lir_lbr}")

baseline_risks = st.container(border=True)
baseline_risks.header("Output 1: Baseline Risks", divider="blue")
baseline_risks.write(
    "Assuming for simplicity that high vs. low bleeding risk is independent from high vs. low ischaemia risk, Inputs 1 and 2 imply the risk levels of patients who are low and high risk for each outcome."
)

baseline_col, risk_ratios_col, high_risk_col = baseline_risks.columns(3)

baseline_col.subheader(
    "Low Risks",
    divider="red",
    help="The chance of bleeding for a patient at low bleeding and low ischaemia risk.",
)
data = {
    "Outcome": ["Bleeding", "Ischaemia"],
    "Probability (%)": [30, 40],
}
df = pd.DataFrame(data)
baseline_col.bar_chart(df, x="Outcome", y="Probability (%)")

risk_ratios_col.subheader(
    "Risk Ratios",
    divider="red",
    help="The relative risk (RR) between the high and low risk groups for each outcome.",
)
data = {
    "Risk Group": ["Bleeding", "Ischaemia"],
    "Risk Ratio": [1.2, 1.3],
}
df = pd.DataFrame(data)
risk_ratios_col.bar_chart(df, x="Risk Group", y="Risk Ratio")

high_risk_col.subheader(
    "High Risks",
    divider="red",
    help="The probability of bleeding and ischaemia events if a patient is high bleeding risk or high ischaemia risk (the low risk multiplied by the risk ratio).",
)
data = {
    "Outcome": ["Bleeding", "Ischaemia"],
    "Probability (%)": [50, 60],
}
df = pd.DataFrame(data)
high_risk_col.bar_chart(df, x="Outcome", y="Probability (%)")


# hir_col.subheader("HIR and LBR", divider="orange", help=f"This group accounts for {100*p_b_hir_lbr:.2f}% of patients.")
# data = {
#     "Ischaemia": [p_b_i_b_hir_lbr, p_b_i_nb_hir_lbr],
#     "No Ischaemia": [p_b_ni_b_hir_lbr, p_b_ni_nb_hir_lbr],
# }
# df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
# hir_col.table(df)

# lir_col.subheader("LIR and HBR", divider="orange", help=f"This group accounts for {100*p_b_lir_hbr:.2f}% of patients.")
# data = {
#     "Ischaemia": [p_b_i_b_lir_hbr, p_b_i_nb_lir_hbr],
#     "No Ischaemia": [p_b_ni_b_lir_hbr, p_b_ni_nb_lir_hbr],
# }
# df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
# lir_col.table(df)


# lir_col.subheader("LIR and LBR", divider="green", help=f"This group accounts for {100*p_b_lir_lbr:.2f}% of patients.")
# data = {
#     "Ischaemia": [p_b_i_b_lir_lbr, p_b_i_nb_lir_lbr],
#     "No Ischaemia": [p_b_ni_b_lir_lbr, p_b_ni_nb_lir_lbr],
# }
# df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
# lir_col.table(df)
