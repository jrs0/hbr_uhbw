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
    
def platelets_score(data) -> float | None:
    """Thrombocytopenia score
    """
    if data["platelets"] is None:
        return None
    elif data["platelets"] < 100:
        return 1.0
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

def platelets_string(data) -> str:
    if data["platelets"] is None:
        return f":grey[missing]"
    else:
        score = platelets_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['platelets']:.1f} ×10⁹/L]"

def strike(value: str):
    return f"~{value}~"

st.set_page_config(layout="wide", page_title="ARC HBR Calculator")

c = st.container(border=True)
c.header("Raw Data")


init_data = {
    "age": 71,
    "gender": "Male",
    "hb": 11.2,
    "platelets": 99,
}

if "edit_data" not in st.session_state:
    st.session_state["edit_data"] = init_data

# For convenience
edit_data = st.session_state["edit_data"]

def age_editor(parent, edit):
    return parent.number_input(
        "Edit age", label_visibility="collapsed", step=1, disabled=not edit
    )
    
def gender_editor(parent, edit):
    return parent.selectbox(
        "Edit gender", ["Male", "Female"], label_visibility="collapsed", disabled=not edit
    )

def hb_editor(parent, edit):
    return parent.number_input(
        "Edit Hb", label_visibility="collapsed", step=0.1, disabled=not edit
    )

def platelets_editor(parent, edit):
    return parent.number_input(
        "Edit Platelets", label_visibility="collapsed", step=0.1, disabled=not edit
    )

def raw_data_input(col, editor_fn, string_fn, key, title, icon, init_data, edit_data):
    r = col.container(border=True)

    icon_col, d = r.columns([0.2, 0.8])
    utils.write_svg(icon_col, icon)

    check_field, edit_field = r.columns([0.3, 0.7])
    edit = check_field.checkbox("Edit?", key=f"{key}_edit_checkbox")
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

print(init_data)
print(edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], age_editor, age_string, "age", "Age", "static/elderly.svg", init_data, edit_data)
raw_data_input(cols[1], gender_editor, gender_string, "gender", "Gender", "static/gender.svg", init_data, edit_data)
raw_data_input(cols[2], hb_editor, hb_string, "hb", "Haemoglobin", "static/blood.svg", init_data, edit_data)

row = c.container()
cols = row.columns(3)

raw_data_input(cols[0], platelets_editor, platelets_string, "platelets", "Platelets", "static/blood_test.svg", init_data, edit_data)