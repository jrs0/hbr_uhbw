import streamlit as st
import pandas as pd

import components
import utils


def age_score(data) -> float | None:
    if data["age"] is None:
        return None
    elif data["age"] < 75:
        return 0.0
    else: 
        return 0.5

def oac_score(data) -> float | None:
    if data["oac"] is None:
        return None
    elif data["oac"] == "Yes":
        return 1.0
    else: 
        return 0.0

def cancer_score(data) -> float | None:
    if data["cancer"] is None:
        return None
    elif data["cancer"] == "Yes":
        return 1.0
    else: 
        return 0.0
    
def nsaid_score(data) -> float | None:
    if data["nsaid"] is None:
        return None
    elif data["nsaid"] == "Yes":
        return 0.5
    else: 
        return 0.0

def prior_surgery_trauma_score(data) -> float | None:
    if data["prior_surgery_trauma"] is None:
        return None
    elif data["prior_surgery_trauma"] == "Yes":
        return 1.0
    else: 
        return 0.0

def planned_surgery_score(data) -> float | None:
    if data["planned_surgery"] is None:
        return None
    elif data["planned_surgery"] == "Yes":
        return 1.0
    else: 
        return 0.0
    
def cirrhosis_ptl_hyp_score(data) -> float | None:
    if data["cirrhosis_ptl_hyp"] is None:
        return None
    elif data["cirrhosis_ptl_hyp"] == "Yes":
        return 1.0
    else: 
        return 0.0
    
def hb_score(data) -> float | None:
    """Anaemia score
    """
    hb = data["hb"]
    gender = data["gender"]
    
    if hb < 11.0: # Major for any gender
        return 1.0 
    elif hb < 11.9: # Minor for any gender
        return 0.5
    elif (hb < 12.9) and (gender == "Male"):
        return 0.5
    else:
        return 0.0

def egfr_score(data) -> float | None:
    """Renal function score
    """
    egfr = data["egfr"]
    
    if egfr < 30.0:
        return 1.0 
    elif egfr < 60.0:
        return 0.5
    else:
        return 0.0
    
def platelets_score(data) -> float | None:
    """Thrombocytopenia score
    """
    if data["platelets"] is None:
        return None
    elif data["platelets"] < 100:
        return 1.0
    else: 
        return 0.0

def prior_bleeding_score(data) -> float | None:
    if data["prior_bleeding"] is None:
        return None
    elif data["prior_bleeding"] == "< 6 months or recurrent":
        return 1.0
    elif data["prior_bleeding"] == "< 12 months":
        return 0.5
    else:
        return 0.0

def prior_ich_stroke_score(data) -> float | None:
    if data["prior_ich_stroke"] is None:
        return None
    elif data["prior_ich_stroke"] == "bAVM, ICH, or moderate/severe ischaemic stroke < 6 months":
        return 1.0
    elif data["prior_ich_stroke"] == "Any prior ischaemic stroke":
        return 0.5
    else:
        return 0.0
    
def score_to_colour(score: float | None) -> str | None:
    if score is None:
        return None
    elif score < 0.5:
        return "green"
    elif score < 1.0:
        return "orange"
    else:
        return "red"

def age_string(data) -> str:
    if data["age"] is None:
        return f":grey[missing]"
    else:
        score = age_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['age']}]"

def oac_string(data) -> str:
    if data["oac"] is None:
        return f":grey[missing]"
    else:
        score = oac_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['oac']}]"

def prior_surgery_trauma_string(data) -> str:
    if data["prior_surgery_trauma"] is None:
        return f":grey[missing]"
    else:
        score = prior_surgery_trauma_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['prior_surgery_trauma']}]"

def planned_surgery_string(data) -> str:
    if data["planned_surgery"] is None:
        return f":grey[missing]"
    else:
        score = planned_surgery_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['planned_surgery']}]"
    
def cancer_string(data) -> str:
    if data["cancer"] is None:
        return f":grey[missing]"
    else:
        score = cancer_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['cancer']}]"
    
def nsaid_string(data) -> str:
    if data["nsaid"] is None:
        return f":grey[missing]"
    else:
        score = nsaid_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['nsaid']}]"
    
def gender_string(data) -> str:
    if data["gender"] is None:
        return f":grey[missing]"
    else:
        return data["gender"]

def hb_string(data) -> str:
    if data["hb"] is None:
        return f":grey[missing]"
    else:
        score = hb_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['hb']:.1f} g/dL]"

def egfr_string(data) -> str:
    if data["egfr"] is None:
        return f":grey[missing]"
    else:
        score = egfr_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['egfr']:.1f} mL/min]"
    
def platelets_string(data) -> str:
    if data["platelets"] is None:
        return f":grey[missing]"
    else:
        score = platelets_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['platelets']:.1f} ×10⁹/L]"

def prior_bleeding_string(data) -> str:
    if data["prior_bleeding"] is None:
        return f":grey[missing]"
    else:
        score = prior_bleeding_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['prior_bleeding']}]"

def prior_ich_stroke_string(data) -> str:
    if data["prior_ich_stroke"] is None:
        return f":grey[missing]"
    else:
        score = prior_ich_stroke_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['prior_ich_stroke']}]"
    
def cirrhosis_ptl_hyp_string(data) -> str:
    if data["cirrhosis_ptl_hyp"] is None:
        return f":grey[missing]"
    else:
        score = cirrhosis_ptl_hyp_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['cirrhosis_ptl_hyp']}]"
    
def strike(value: str):
    return f"~{value}~"

st.set_page_config(layout="wide", page_title="ARC HBR Calculator")

c = st.container(border=True)
c.header("Raw Data")


init_data = {
    "age": 71,
    "oac": "Yes",
    "gender": "Male",
    "hb": 11.2,
    "platelets": 99,
    "egfr": 50,
    "prior_bleeding": None,
    "cirrhosis_ptl_hyp": None,
    "nsaid": "No",
    "cancer": "No",
    "prior_ich_stroke": None,
    "prior_surgery_trauma": "No",
    "planned_surgery": None,
}

if "edit_data" not in st.session_state:
    st.session_state["edit_data"] = init_data

# For convenience
edit_data = st.session_state["edit_data"]

def age_editor(parent, edit):
    return parent.number_input(
        "Edit age", label_visibility="collapsed", step=1, disabled=not edit
    )

def oac_editor(parent, edit):
    return parent.selectbox(
        "Edit oac", ["Yes", "No"], label_visibility="collapsed", disabled=not edit
    )

def prior_surgery_trauma_editor(parent, edit):
    return parent.selectbox(
        "Edit surgery/trauma", ["Yes", "No"], label_visibility="collapsed", disabled=not edit
    )

def planned_surgery_editor(parent, edit):
    return parent.selectbox(
        "Edit planned surgery", ["Yes", "No"], label_visibility="collapsed", disabled=not edit
    )

def cancer_editor(parent, edit):
    return parent.selectbox(
        "Edit cancer", ["Yes", "No"], label_visibility="collapsed", disabled=not edit
    )

def nsaid_editor(parent, edit):
    return parent.selectbox(
        "Edit nsaid", ["Yes", "No"], label_visibility="collapsed", disabled=not edit
    )

def cirrhosis_ptl_hyp_editor(parent, edit):
    return parent.selectbox(
        "Edit cirrhosis", ["Yes", "No"], label_visibility="collapsed", disabled=not edit
    )

def gender_editor(parent, edit):
    return parent.selectbox(
        "Edit gender", ["Male", "Female"], label_visibility="collapsed", disabled=not edit
    )

def hb_editor(parent, edit):
    return parent.number_input(
        "Edit Hb", label_visibility="collapsed", step=0.1, disabled=not edit
    )

def egfr_editor(parent, edit):
    return parent.number_input(
        "Edit eGFR", label_visibility="collapsed", step=1, disabled=not edit
    )

def platelets_editor(parent, edit):
    return parent.number_input(
        "Edit Platelets", label_visibility="collapsed", step=0.1, disabled=not edit
    )

def prior_bleeding_editor(parent, edit):
    return parent.selectbox(
        "Edit Prior Bleeding",
        [
            "< 6 months or recurrent",
            "< 12 months",
            "No bleeding"
        ],
        label_visibility="collapsed", disabled=not edit
    )

def prior_ich_stroke_editor(parent, edit):
    return parent.selectbox(
        "Edit Prior ICH/Stroke",
        [
            "bAVM, ICH, or moderate/severe ischaemic stroke < 6 months",
            "Any prior ischaemic stroke",
            "No ICH/ischaemic stroke"
        ],
        label_visibility="collapsed", disabled=not edit
    )

def raw_data_input(col, editor_fn, string_fn, key, title, desc, icon, init_data, edit_data):
    r = col.container(border=True)

    icon_col, d = r.columns([0.2, 0.8])
    utils.write_svg(icon_col, icon)

    check_field, edit_field = r.columns([0.3, 0.7])
    edit = check_field.checkbox("Adjust?", key=f"{key}_edit_checkbox")
    result = editor_fn(edit_field, edit)
    if edit:
        edit_data[key] = result
    else:
        edit_data[key] = init_data[key]


    # Get the initial value of the parameter
    init_string = string_fn(init_data)

    # Print the edit value if it is different
    if edit_data[key] == init_data[key]:
        full_string = init_string
    else:
        init_string = strike(init_string)
        edit_string = string_fn(edit_data)
        full_string = f"{init_string} {edit_string}"

    d.write(f"**{title}: {full_string}**")
    d.write(desc)

print(init_data)
print(edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], age_editor, age_string, "age", "Age", "", "static/elderly.svg", init_data, edit_data)
raw_data_input(cols[1], gender_editor, gender_string, "gender", "Gender", "", "static/gender.svg", init_data, edit_data)
raw_data_input(cols[2], hb_editor, hb_string, "hb", "Haemoglobin", "", "static/blood.svg", init_data, edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], platelets_editor, platelets_string, "platelets", "Platelets", "", "static/blood_test.svg", init_data, edit_data)
raw_data_input(cols[1], egfr_editor, egfr_string, "egfr", "eGFR", "", "static/kidney.svg", init_data, edit_data)
raw_data_input(cols[2], prior_bleeding_editor, prior_bleeding_string, "prior_bleeding", "Prior bleeding", "Prior bleeding must require hospitalisation or transfusion, and excludes intracranial bleeding.", "static/transfusion.svg", init_data, edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], oac_editor, oac_string, "oac", "OAC", "Anticipated long-term use of oral anticoagulants", "static/pill_bottle.svg", init_data, edit_data)
raw_data_input(cols[1], cirrhosis_ptl_hyp_editor, cirrhosis_ptl_hyp_string, "cirrhosis_ptl_hyp", "Cirrhosis/Portal Hypertension", "Criterion requires both cirrhosis and portal hypertension.", "static/liver.svg", init_data, edit_data)
raw_data_input(cols[2], nsaid_editor, nsaid_string, "nsaid", "Oral NSAID/Steroids", "Anticipated long-term use >= 4 days/week.", "static/pills.svg", init_data, edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], cancer_editor, cancer_string, "cancer", "Cancer", "Criterion requires diagnosis within 12 months or active cancer therapy.", "static/lungs.svg", init_data, edit_data)
raw_data_input(cols[1], prior_ich_stroke_editor, prior_ich_stroke_string, "prior_ich_stroke", "ICH/Ischaemic Stroke", "", "static/brain.svg", init_data, edit_data)
raw_data_input(cols[2], prior_surgery_trauma_editor, prior_surgery_trauma_string, "prior_surgery_trauma", "Prior Major Surgery/Trauma", "Criterion requires either major surgery or trauma in past 30 days.", "static/scalpel.svg", init_data, edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], planned_surgery_editor, planned_surgery_string, "planned_surgery", "Planned Surgery on DAPT", "Criterion requires major non-deferrable surgery planned while will be on DAPT", "static/scalpel.svg", init_data, edit_data)
