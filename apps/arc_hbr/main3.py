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
except:
    selected_row = 0

edit_records = ss["edit_records"]

# Print the summary table
grid_return = summary_data.show_summary_table(summary, init_records, edit_records, selected_row)

def update_edit_records(t_number, key):
    """Callback to update edit_records on any change in the editor
    """
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

    print("Printing detail")

    data = utils.df_to_records(sel)

    if len(data) != 1:
        st.error("Expected only one selected row")

    t_number = next(iter(data))
    arc_total = data[t_number]["arc_total"]
    
    # Regenerate the summary records (for some reason
    # ag grid does not return the updated data). 
    # init and edit records are up to date here because
    # of the callback. This is overkill because of
    # all the recomputing, but it works for now.
    summary_records = summary_data.get_records(init_records, edit_records)    
    scores = arc.all_scores(summary_records)
    summary_df = utils.records_to_df(summary_records)
    df = summary_df.merge(scores, on="t_number", how="left")
    df["arc_total"] = df.filter(regex="score").sum(axis=1)
    arc_total = df.set_index("t_number").loc[t_number, "arc_total"]
    
    init_record = init_records[t_number]
    edit_record = edit_records[t_number]
    
    callback = lambda key: update_edit_records(t_number, key)
    editor(detail, t_number, arc_total, init_record, edit_record, callback)
else:
    print("Got none")
    
print("End")