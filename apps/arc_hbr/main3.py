import streamlit as st
import pandas as pd
import numpy as np
from mock_patient import Random
from streamlit import session_state as ss
from mock_editor import mock_editor
from st_aggrid import AgGrid, JsCode, GridOptionsBuilder
import arc
import utils
import summary_data
from editor import editor

print("Starting run")

st.set_page_config(layout="wide", page_title="ARC HBR Calculator")

# Create containers in a fixed order to present the
# data. The logic for updating must be the other
# way round so the evaluation order of updates is
# correct
summary = st.container()
detail = st.container()

# This is a mock -- replace will function that fetches real data
@st.cache_data
def get_init_records():
    seed = 6
    random = Random(seed=seed)
    return {
        random.random_tnumber(): random.random_patient()
        for _ in range(10)
    }

# Fetch the initial values of the data
init_records = get_init_records()

if "edit_records" not in ss:
    ss["edit_records"] = utils.get_empty_edit_records(init_records)

if "selected_row" not in ss:
    pass


try:
    selected_row = ss["summary_table_key"]["selectedItems"][0]["rowIndex"]
except (KeyError, IndexError):
    selected_row = 0

edit_records = ss["edit_records"]

grid_return = summary_data.show_summary_table(summary, init_records, edit_records, selected_row)

def update_edit_records(t_number, key):
    print(f"Changing state of {key}")
    checkbox_state = ss[f"{key}_edit_checkbox"]
    print(f"New edit-checkbox state is {checkbox_state}")
    edit_state = None
    if checkbox_state:
        edit_state = ss[f"input_{key}"]
    print(f"New edit input is {edit_state}")
    
    # Update the edit_record in session state
    print(f"Going to update record for {t_number}")
    edit_records = ss["edit_records"]
    edit_records[t_number][key] = edit_state
    ss["edit_records"] = edit_records

sel = grid_return.selected_rows
if sel is not None:

    detail.write(sel)

    data = utils.df_to_records(sel)

    if len(data) != 1:
        st.error("Expected only one selected row")

    t_number = next(iter(data))
    arc_total = data[t_number]["arc_total"]
    
    init_record = init_records[t_number]
    edit_record = edit_records[t_number]

    callback = lambda key: update_edit_records(t_number, key)
    edit_record = editor(detail, t_number, arc_total, init_record, edit_record, callback)
    
    edit_records[t_number] = edit_record

    
