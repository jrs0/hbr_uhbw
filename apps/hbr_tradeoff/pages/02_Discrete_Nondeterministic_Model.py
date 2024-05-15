import pandas as pd
import numpy as np
import streamlit as st

st.title("Discrete Nondeterministic Model")
st.write("*Baseline patients are dichotomised into high and low risk, but baseline outcomes are probabilistic. Interventions modify this probability.*")

st.write("This simulation uses the simplest possible non-deterministic model of patient outcomes, where baseline patients have a bleeding and ischaemia risk depending on which of four possible risk categories they belong to. The four risk categories are:")
st.write("- **LIR/LBR**: Low ischaemia risk and low bleeding risk;\n- **HIR/LBR**: High ischaemia risk and low bleeding risk;\n- **LIR/HBR**: Low ischaemia risk and high bleeding risk;\n- **HIR/HBR**: High ischaemia risk and high bleeding risk.")

st.info("In this model, baseline patients have a bleeding risk and an ischaemia risk which depends only on which of of the four groups they are in.", icon="ℹ️")

st.write("Similarly to the deterministic model, baseline outcome prevalences are used as an input (**Input 1**). This information is paired with the proportions of patients at high bleeding risk and high ischaemia risk, which can be estimated from literature (**Input 2**). Together, this information determines the baseline patient risk in each risk group.")

st.write("In the model, a hypothetical risk-estimation tool attempts to decide which of the four risk categories a patient belongs to, with a certain degree of success (**Input 3**). An intervention is applied to the patients determined to be at high bleeding risk.")

st.info("The black-box model estimates bleeding and ischaemia risk category, and is specified by inputting true/false positive rates for correctly categorising patients.", icon="ℹ️")

st.write("The intervention is assumed to modify the patient's bleeding and ischaemia risk. The intervention's effectiveness is specified as risk ratios relative to the patient's chance of adverse outcomes in their real risk category (**Input 4**).")

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
        ) / 100.0
    )

p_b_ni_nb = simple_prob_input(baseline_container, "Proportion with no ischaemia and no bleeding (%)", 80.0)
p_b_i_nb = simple_prob_input(baseline_container, "Proportion with ischaemia but no bleeding (%)", 18.0)
p_b_ni_b = simple_prob_input(baseline_container, "Proportion with bleeding but no ischaemia (%)", 1.0)
p_b_i_b = simple_prob_input(baseline_container, "Proportion with bleeding and ischaemia (%)", 1.0)

total_prob = p_b_ni_nb + p_b_ni_b + p_b_i_nb + p_b_i_b
if np.abs(total_prob - 1.0) > 1e-5:
    st.error(
        f"Total proportions must add up to 100%; these add up to {100*total_prob:.2f}%"
    )

high_risk_container = st.container(border=True)
high_risk_container.header("Input 2: Number of Patients at High Risk", divider=True)
high_risk_container.write("Input the proportion of patients who are at high risk of bleeding and/or ischaemia.")
high_risk_container.write("This value involves making a choice for what high risk means, and then inputting the proportion of patients that meet this high risk definition based on literature or experience.")
high_risk_container.write("The default value of 30% HBR follows from the estimated proportion of patients meeting the ARC HBR criteria, whereas the HIR default 50% is based on the estimate for the ESC/EACTS HIR definition.")

p_b_hir = simple_prob_input(high_risk_container, "Proportion at high ischaemia risk (HIR) (%)", 50.0)
p_b_hbr = simple_prob_input(high_risk_container, "Proportion at high bleeding risk (HBR) (%)", 30.0)

# Assuming independence, get probabilities for all
# combinations of low and high risk
p_b_hir_hbr = p_b_hir * p_b_hbr
p_b_hir_lbr = p_b_hir * (1 - p_b_hbr)
p_b_lir_hbr = (1 - p_b_hir) * p_b_hbr
p_b_lir_lbr = (1 - p_b_hir) * (1 - p_b_hbr)

# HIR and HBR
p_b_ni_nb_hir_hbr = 0.1
p_b_i_nb_hir_hbr = 0.11
p_b_ni_b_hir_hbr = 0.12
p_b_i_b_hir_hbr = 0.13

# HIR and LBR
p_b_ni_nb_hir_lbr = 0.20
p_b_i_nb_hir_lbr = 0.21
p_b_ni_b_hir_lbr = 0.22
p_b_i_b_hir_lbr = 0.23

# LIR and HBR
p_b_ni_nb_lir_hbr = 0.3
p_b_i_nb_lir_hbr = 0.31
p_b_ni_b_lir_hbr = 0.32
p_b_i_b_lir_hbr = 0.33

# LIR and LBR
p_b_ni_nb_lir_lbr = 0.4
p_b_i_nb_lir_lbr = 0.41
p_b_ni_b_lir_lbr = 0.42
p_b_i_b_lir_lbr = 0.43

baseline_risks = st.container(border=True)
baseline_risks.header("Output 1: Baseline Risks", divider="blue")
baseline_risks.write("From Inputs 1 and 2, it is possible to calculate the baseline risk of bleeding and ischaemia in each of the four risk categories.")

hir_col, lir_col = baseline_risks.columns(2)

hir_col.subheader("HIR and HBR", divider="red", help=f"This group accounts for {100*p_b_hir_hbr:.2f}% of patients.")
data = {
    "Ischaemia": [p_b_i_b_hir_hbr, p_b_i_nb_hir_hbr],
    "No Ischaemia": [p_b_ni_b_hir_hbr, p_b_ni_nb_hir_hbr],
}
df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
hir_col.table(df)

hir_col.subheader("HIR and LBR", divider="orange", help=f"This group accounts for {100*p_b_hir_lbr:.2f}% of patients.")
data = {
    "Ischaemia": [p_b_i_b_hir_lbr, p_b_i_nb_hir_lbr],
    "No Ischaemia": [p_b_ni_b_hir_lbr, p_b_ni_nb_hir_lbr],
}
df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
hir_col.table(df)

lir_col.subheader("LIR and HBR", divider="orange", help=f"This group accounts for {100*p_b_lir_hbr:.2f}% of patients.")
data = {
    "Ischaemia": [p_b_i_b_lir_hbr, p_b_i_nb_lir_hbr],
    "No Ischaemia": [p_b_ni_b_lir_hbr, p_b_ni_nb_lir_hbr],
}
df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
lir_col.table(df)


lir_col.subheader("LIR and LBR", divider="green", help=f"This group accounts for {100*p_b_lir_lbr:.2f}% of patients.")
data = {
    "Ischaemia": [p_b_i_b_lir_lbr, p_b_i_nb_lir_lbr],
    "No Ischaemia": [p_b_ni_b_lir_lbr, p_b_ni_nb_lir_lbr],
}
df = pd.DataFrame(data, index=["Bleeding", "No Bleeding"]).applymap(lambda x: f"{100*x:.2f}%")
lir_col.table(df)

