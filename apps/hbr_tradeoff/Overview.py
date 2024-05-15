import streamlit as st

st.title("Bleeding/Ischaemia Outcomes")
st.write("*Modelling effectiveness of DAPT changes based on bleeding/ischaemia-risk estimates.*")

st.write("This application contains a collection of simple probability-based simulations design to place minimum performance criteria on models of bleeding and ischaemia risk in patients with acute coronary syndromes (ACS) being placed on a blood thinning medication like dual antiplatelet therapy (DAPT).")

st.info("DAPT reduces the chance of further ischaemia (e.g. heart attacks), but increases the chance of bleeding; both outcomes can be severe. Clinicians must balance the two risks when choosing the type/duration of DAPT, to optimise patient outcomes.", icon="ℹ️")

st.write("One option to aid in the choice of DAPT is to model each patient's bleeding and ischaemia risk, and use this to inform choices of DAPT therapy. The simulations here are designed to investigate the modelling performance required for this to be an effective approach.")

st.write("**Patients are considered in two groups.** In one group (A), DAPT choices may be modified depending on a black-box bleeding/ischaemia model. The other group (B) reflects baseline outcomes treated without using any model.")

st.info("This is intended to reflect how a trial of the tool might be designed.", icon="ℹ️")

st.write("**Baseline outcome rates are inputs to the simulations**. These can be taken from studies investigating risks of each outcome. Some simulations also make assumptions about underlying risk distribution. Different types of simulations are presented which make different assumptions, to show how the assumptions affect the result.")

st.warning("These assumptions are not easily testable, and represent limitations of the simulations. However, different kinds of assumptions are tested to understand how results depend on the assumptions.", icon="⚠️")

st.write("**Expected effectiveness of DAPT changes in different patient groups are inputs to the simulations**. These numbers could be based on studies that look at changes in outcome based on different DAPT therapies.")

st.warning("Simulating changes in outcomes ultimately require assumptions about how individual patient risk is modified, which is also hard to test. Results should be interpreted as showing the rough magnitude of outcome changes, rather than making detailed predictions.", icon="⚠️")

st.write("**The model accuracy (true and false positive rates) are inputs to the simulation**. The models are intended to identify patients are high bleeding and/or ischaemia risk, who would have a targeted intervention applied to them.")

st.success("The purpose of the simulations is to explore how real-world factors (baseline outcome rates and expected intervention effectiveness) translate to required model performance.", icon="✅")

