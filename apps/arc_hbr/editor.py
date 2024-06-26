import streamlit as st
import strings 

import utils

def strike(value: str):
    return f"~{value}~"

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

    # Get the previous edited state then update according to
    # the value of the checkbox
    edit = edit_data[key] is not None
    edit = check_field.checkbox("Edit?", key=f"{key}_edit_checkbox", value=edit)
    
    result = editor_fn(edit_field, edit)
    if edit:
        edit_data[key] = result
    else:
        edit_data[key] = None

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

def editor(
        parent,
        t_number: str,
        arc_total: float,
        init_data: dict[str, str | int | float | None],
        edit_data: dict[str, str | int | float | None],
) -> dict[str, str | int | float | None]:

    colour = strings.score_to_colour(arc_total)
    
    parent = st.container(border=True)
    parent.header(f"{init_data['name']} ({t_number}) :{colour}[{arc_total:.1f}]", divider=colour)
    
    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], age_editor, strings.age_string, "age", "Age", "", "static/elderly.svg", init_data, edit_data)
    raw_data_input(cols[1], gender_editor, strings.gender_string, "gender", "Gender", "", "static/gender.svg", init_data, edit_data)
    raw_data_input(cols[2], hb_editor, strings.hb_string, "hb", "Haemoglobin", "", "static/blood.svg", init_data, edit_data)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], platelets_editor, strings.platelets_string, "platelets", "Platelets", "", "static/blood_test.svg", init_data, edit_data)
    raw_data_input(cols[1], egfr_editor, strings.egfr_string, "egfr", "eGFR", "", "static/kidney.svg", init_data, edit_data)
    raw_data_input(cols[2], prior_bleeding_editor, strings.prior_bleeding_string, "prior_bleeding", "Prior bleeding", "Prior bleeding must require hospitalisation or transfusion, and excludes intracranial bleeding.", "static/transfusion.svg", init_data, edit_data)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], oac_editor, strings.oac_string, "oac", "OAC", "Anticipated long-term use of oral anticoagulants", "static/pill_bottle.svg", init_data, edit_data)
    raw_data_input(cols[1], cirrhosis_ptl_hyp_editor, strings.cirrhosis_ptl_hyp_string, "cirrhosis_ptl_hyp", "Cirrhosis/Portal Hypertension", "Criterion requires both cirrhosis and portal hypertension.", "static/liver.svg", init_data, edit_data)
    raw_data_input(cols[2], nsaid_editor, strings.nsaid_string, "nsaid", "Oral NSAID/Steroids", "Anticipated long-term use >= 4 days/week.", "static/pills.svg", init_data, edit_data)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], cancer_editor, strings.cancer_string, "cancer", "Cancer", "Criterion requires diagnosis within 12 months or active cancer therapy.", "static/lungs.svg", init_data, edit_data)
    raw_data_input(cols[1], prior_ich_stroke_editor, strings.prior_ich_stroke_string, "prior_ich_stroke", "ICH/Ischaemic Stroke", "", "static/brain.svg", init_data, edit_data)
    raw_data_input(cols[2], prior_surgery_trauma_editor, strings.prior_surgery_trauma_string, "prior_surgery_trauma", "Prior Major Surgery/Trauma", "Criterion requires either major surgery or trauma in past 30 days.", "static/scalpel.svg", init_data, edit_data)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], planned_surgery_editor, strings.planned_surgery_string, "planned_surgery", "Planned Surgery on DAPT", "Criterion requires major non-deferrable surgery planned while will be on DAPT", "static/scalpel.svg", init_data, edit_data)

    return edit_data
   
