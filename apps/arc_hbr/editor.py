import streamlit as st
import strings 

import utils

def strike(value: str):
    return f"~{value}~"

def age_editor(parent, edit, callback):
    return parent.number_input(
        "Edit age", key="input_age", label_visibility="collapsed", step=1, disabled=not edit, on_change=callback, args=("age",)
    )

def oac_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit oac", ["Yes", "No"], key="input_oac", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("oac",)
    )

def prior_surgery_trauma_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit surgery/trauma", ["Yes", "No"], key="input_prior_surgery_trauma", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("prior_surgery_trauma",)
    )

def planned_surgery_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit planned surgery", ["Yes", "No"], key="input_planned_surgery", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("planned_surgery",)
    )

def cancer_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit cancer", ["Yes", "No"], key="input_cancer", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("cancer",)
    )

def nsaid_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit nsaid", ["Yes", "No"], key="input_nsaid", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("nsaid",)
    )

def cirrhosis_ptl_hyp_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit cirrhosis", ["Yes", "No"], key="input_cirrhosis_ptl_hyp", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("cirrhosis_ptl_hyp",)
    )

def gender_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit gender", ["Male", "Female"], key="input_gender", label_visibility="collapsed", disabled=not edit, on_change=callback, args=("gender",)
    )

def hb_editor(parent, edit, callback):
    return parent.number_input(
        "Edit Hb", label_visibility="collapsed", key="input_hb", step=0.1, disabled=not edit, on_change=callback, args=("hb",)
    )

def egfr_editor(parent, edit, callback):
    return parent.number_input(
        "Edit eGFR", label_visibility="collapsed", key="input_egfr", step=1, disabled=not edit, on_change=callback, args=("egfr",)
    )

def platelets_editor(parent, edit, callback):
    return parent.number_input(
        "Edit Platelets", label_visibility="collapsed", key="input_platelets", step=0.1, disabled=not edit, on_change=callback, args=("platelets",)
    )

def prior_bleeding_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit Prior Bleeding",
        [
            "< 6 months or recurrent",
            "< 12 months",
            "No bleeding"
        ],
        key="input_prior_bleeding",
        label_visibility="collapsed", disabled=not edit,
        on_change=callback, args=("prior_bleeding",)
    )

def prior_ich_stroke_editor(parent, edit, callback):
    return parent.selectbox(
        "Edit Prior ICH/Stroke",
        [
            "bAVM, ICH, or moderate/severe ischaemic stroke < 6 months",
            "Any prior ischaemic stroke",
            "No ICH/ischaemic stroke"
        ],
        key="input_prior_ich_stroke",
        label_visibility="collapsed", disabled=not edit,
        on_change=callback, args=("prior_ich_stroke",)
    )

def raw_data_input(col, editor_fn, string_fn, key, title, desc, icon, init_data, edit_data, callback):
    r = col.container(border=True)

    icon_col, d = r.columns([0.2, 0.8])
    utils.write_svg(icon_col, icon)

    check_field, edit_field = r.columns([0.3, 0.7])

    # Get the previous edited state then update according to
    # the value of the checkbox
    edit = edit_data[key] is not None
    edit = check_field.checkbox("Edit?", key=f"{key}_edit_checkbox", value=edit, on_change=callback, args=(key,))
    
    result = editor_fn(edit_field, edit, callback)
    if edit:
        edit_data[key] = result
    else:
        edit_data[key] = None

    # Get the initial value of the parameter
    init_string = string_fn(init_data)

    # Print the edit value if it is different
    if edit_data[key] is None:
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
        update_edit_records,
) -> dict[str, str | int | float | None]:

    colour = strings.score_to_colour(arc_total)
    
    parent = st.container(border=True)
    parent.header(f"{init_data['name']} ({t_number}) :{colour}[{arc_total:.1f}]", divider=colour)
    
    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], age_editor, strings.age_string, "age", "Age", "", "static/elderly.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[1], gender_editor, strings.gender_string, "gender", "Gender", "", "static/gender.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[2], hb_editor, strings.hb_string, "hb", "Haemoglobin", "", "static/blood.svg", init_data, edit_data, update_edit_records)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], platelets_editor, strings.platelets_string, "platelets", "Platelets", "", "static/blood_test.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[1], egfr_editor, strings.egfr_string, "egfr", "eGFR", "", "static/kidney.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[2], prior_bleeding_editor, strings.prior_bleeding_string, "prior_bleeding", "Prior bleeding", "Prior bleeding must require hospitalisation or transfusion, and excludes intracranial bleeding.", "static/transfusion.svg", init_data, edit_data, update_edit_records)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], oac_editor, strings.oac_string, "oac", "OAC", "Anticipated long-term use of oral anticoagulants", "static/pill_bottle.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[1], cirrhosis_ptl_hyp_editor, strings.cirrhosis_ptl_hyp_string, "cirrhosis_ptl_hyp", "Cirrhosis/Portal Hypertension", "Criterion requires both cirrhosis and portal hypertension.", "static/liver.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[2], nsaid_editor, strings.nsaid_string, "nsaid", "Oral NSAID/Steroids", "Anticipated long-term use >= 4 days/week.", "static/pills.svg", init_data, edit_data, update_edit_records)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], cancer_editor, strings.cancer_string, "cancer", "Cancer", "Criterion requires diagnosis within 12 months or active cancer therapy.", "static/lungs.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[1], prior_ich_stroke_editor, strings.prior_ich_stroke_string, "prior_ich_stroke", "ICH/Ischaemic Stroke", "", "static/brain.svg", init_data, edit_data, update_edit_records)
    raw_data_input(cols[2], prior_surgery_trauma_editor, strings.prior_surgery_trauma_string, "prior_surgery_trauma", "Prior Major Surgery/Trauma", "Criterion requires either major surgery or trauma in past 30 days.", "static/scalpel.svg", init_data, edit_data, update_edit_records)

    row = parent.container()
    cols = row.columns(3)

    raw_data_input(cols[0], planned_surgery_editor, strings.planned_surgery_string, "planned_surgery", "Planned Surgery on DAPT", "Criterion requires major non-deferrable surgery planned while will be on DAPT", "static/scalpel.svg", init_data, edit_data, update_edit_records)

    return edit_data
   
