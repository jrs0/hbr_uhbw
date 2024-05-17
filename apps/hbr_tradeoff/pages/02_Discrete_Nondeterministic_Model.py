import numpy as np
import scipy
import pandas as pd
import streamlit as st

st.title("Discrete Nondeterministic Model")
st.write(
    "*Baseline patients are dichotomised into high and low risk, but baseline outcomes are probabilistic. Interventions modify this probability.*"
)

st.write(
    "This simulation uses the simplest possible non-deterministic model of patient outcomes, where baseline patients have a bleeding and ischaemia risk depending on which of four possible risk categories they belong to. The four risk categories are:"
)
st.write(
    "- **LIR/LBR**: Low ischaemia risk and low bleeding risk;\n- **HIR/LBR**: High ischaemia risk and low bleeding risk;\n- **LIR/HBR**: Low ischaemia risk and high bleeding risk;\n- **HIR/HBR**: High ischaemia risk and high bleeding risk."
)

st.info(
    "In this model, baseline patients have a bleeding risk and an ischaemia risk which depends only on which of of the four groups they are in.",
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
) -> float:
    """Low/high bleeding risk object

    Object function to numerically find probabilities of
    outcomes in the low and high bleeding and ischaemia
    groups, by assuming independence of HIR and HBR risk
    groups.

    Args:
        x: The unknown to be found by the optimisation
            procedure. The array contains these values:
            [p_i_lir, p_b_lbr, rr_hir, rr_hbr], which are
            the risks in the LBR/LIR group, and the relative
            risks to get to the HBR and HIR groups (the risk
            groups for each outcome are assumed independent).
        p_ni_nb: Observed no ischaemia/no bleeding prevalence
        p_ni_b: Observed no ischaemia but bleeding prevalence
        p_i_nb: Observed ischaemia but no bleeding prevalence
        p_i_b: Observed ischaemia and bleeding prevalence
        p_hir: Observed prevalence of high ischaemia risk
        p_hbr: Observed prevalence of high bleeding risk

            which are the observed prevalences of all combinations of
            outcomes in the baseline group, along with the known
            prevalences of high bleeding and high ischaemia risk
            in the baseline group.

    Return:
        The L2 distance between the observed prevalences and the
            prevalences implied by the choice of x.
    """

    # Unpack all the unknowns
    p_i_lir = x[0]
    p_b_lbr = x[1]
    rr_hir = x[2]
    rr_hbr = x[3]

    # Calculate what the observed prevalences would
    # be if x were correct

    # Terms contributing to no ischaemia and no bleeding
    # Patient is LIR and LBR
    a = (1 - p_hir) * (1 - p_i_lir) * (1 - p_hbr) * (1 - p_b_lbr)
    # Patient is LIR and HBR
    b = (1 - p_hir) * (1 - p_i_lir) * p_hbr * (1 - rr_hbr * p_b_lbr)
    # Patient is HIR and LBR
    c = p_hir * (1 - rr_hir * p_i_lir) * (1 - p_hbr) * (1 - p_b_lbr)
    # Patient is HIR and HBR
    d = p_hir * (1 - rr_hir * p_i_lir) * p_hbr * (1 - rr_hbr * p_b_lbr)
    # Sum up all contributions
    p_x_ni_nb = a + b + c + d

    # Terms contributing to no ischaemia but bleeding
    # Patient is LIR and LBR
    a = (1 - p_hir) * (1 - p_i_lir) * (1 - p_hbr) * p_b_lbr
    # Patient is LIR and HBR
    b = (1 - p_hir) * (1 - p_i_lir) * p_hbr * rr_hbr * p_b_lbr
    # Patient is HIR and LBR
    c = p_hir * (1 - rr_hir * p_i_lir) * (1 - p_hbr) * p_b_lbr
    # Patient is HIR and HBR
    d = p_hir * (1 - rr_hir * p_i_lir) * p_hbr * rr_hbr * p_b_lbr
    # Sum up all contributions
    p_x_ni_b = a + b + c + d

    # Terms contributing to ischaemia but no bleeding
    # Patient is LIR and LBR
    a = (1 - p_hir) * p_i_lir * (1 - p_hbr) * (1 - p_b_lbr)
    # Patient is LIR and HBR
    b = (1 - p_hir) * p_i_lir * p_hbr * (1 - rr_hbr * p_b_lbr)
    # Patient is HIR and LBR
    c = p_hir * rr_hir * p_i_lir * (1 - p_hbr) * (1 - p_b_lbr)
    # Patient is HIR and HBR
    d = p_hir * rr_hir * p_i_lir * p_hbr * (1 - rr_hbr * p_b_lbr)
    # Sum up all contributions
    p_x_i_nb = a + b + c + d

    # Terms contributing to ischaemia and bleeding
    # Patient is LIR and LBR
    a = (1 - p_hir) * p_i_lir * (1 - p_hbr) * p_b_lbr
    # Patient is LIR and HBR
    b = (1 - p_hir) * p_i_lir * p_hbr * rr_hbr * p_b_lbr
    # Patient is HIR and LBR
    c = p_hir * rr_hir * p_i_lir * (1 - p_hbr) * p_b_lbr
    # Patient is HIR and HBR
    d = p_hir * rr_hir * p_i_lir * p_hbr * rr_hbr * p_b_lbr
    # Sum up all contributions
    p_x_i_b = a + b + c + d

    # Compare the calculated prevalences with the observed
    # prevalences and return the cost (L2 distance)
    a = (p_x_ni_nb - p_ni_nb) ** 2
    b = (p_x_ni_b - p_ni_b) ** 2
    c = (p_x_i_nb - p_i_nb) ** 2
    d = (p_x_i_b - p_i_b) ** 2
    return a + b + c + d


# Set bounds on the probabilities which must be between
# zero and one. Ensure that the risk ratios are larger than
# one (so that the high risk groups have greater risk than
# the low risk groups)
bounds = scipy.optimize.Bounds([0, 0, 1, 1], [1, 1, np.inf, np.inf])

# Solve for the unknown low risk group probabilities and independent
# risk ratios by minimising the objective function
args = (p_b_ni_nb, p_b_ni_b, p_b_i_nb, p_b_i_b, p_b_hir, p_b_hbr)
initial_x = 4 * [0]
res = scipy.optimize.minimize(objective_fn, x0=initial_x, args=args, bounds=bounds)
x = res.x

# Check the solution is correct
cost = objective_fn(x, *args)

# Solved probabilities of bleeding/ischaemia in LBR/LIR groups
p_b_i_lir = x[0]
p_b_b_lbr = x[1]

# Solved risk ratios for high bleeding/high ischaemia risk
rr_hir = x[2]
rr_hbr = x[3]

st.write(f"Cost = {cost}")
st.write(f"p_b_i_lir = {p_b_i_lir}")
st.write(f"p_b_b_lbr = {p_b_b_lbr}")
st.write(f"rr_hir = {rr_hir}")
st.write(f"rr_hbr = {rr_hbr}")

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
