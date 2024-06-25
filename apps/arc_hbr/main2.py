import streamlit as st
from editor import editor
from mock_patient import Random
import arc

import pandas as pd

# This is a mock -- replace will function that fetches real data
@st.cache_data
def get_init_records():
    seed = 6
    random = Random(seed=seed)
    return [random.random_patient() for n in range(10)]
    
st.set_page_config(layout="wide", page_title="ARC HBR Calculator")

# Create the page layout container
summary = st.container()
detail = st.container()

# Get the initial records and create the edited records variable
init_records = get_init_records()
if "edit_records" not in st.session_state:
    st.session_state["edit_records"] = init_records
edit_records = st.session_state["edit_records"]

def create_adjust_records(init_records) -> list[dict[str, bool]]:

    adjust_records = []
    for record in init_records:
        t_number = record["t_number"]
        adjust_records.append({
            "t_number": t_number,
            "age": False,
            "gender": False,
            "oac": False,
            "cancer": False,
            "nsaid": False,
            "prior_surgery_trauma": False,
            "planned_surgery": False,
            "cirrhosis_ptl_hyp": False,
            "hb": False,
            "egfr": False,
            "platelets": False,
            "prior_bleeding": False,
            "prior_ich_stroke": False,
        })

    return adjust_records
                            
# Track the state of which values are adjusted
if "adjust_records" not in st.session_state:
    st.session_state["adjust_records"] = create_adjust_records(init_records)
                              
adjust_records = st.session_state["adjust_records"]

init_records_df = pd.DataFrame.from_records(init_records)
print(init_records_df)

edit_records_df = pd.DataFrame.from_records(edit_records)
print(edit_records_df)

# Calculate the ARC score based on the edited data
edit_scores_df = arc.all_scores(edit_records)

print(edit_scores_df)

# Join all the data together
all_df = edit_records_df.merge(edit_scores_df, on="t_number", how="left")

# Create the summary box
summary.dataframe(all_df)

def get_record_by_tnumber(
        t_number: str,
        records: list[dict[str, str | int | float | None]]
) -> dict[str, str | int | float | None] | None:

    for record in records:
        if record["t_number"] == t_number:
            return record

    return None

def update_record_by_tnumber(
        t_number: str,
        new_record: dict[str, str | int | float | None],
        records: list[dict[str, str | int | float | None]],
):

    for n in range(len(records)):
        if records[n]["t_number"] == t_number:
            records[n] = new_record
            
# Get selected row (if any)
sel = None

if sel is not None:

    # Expect at most one row
    if len(sel) > 1:
        st.error("Unexpected selection of more than one row")
    
    t_number = sel["t_number"][0]
    print(t_number)
    
    init_data = get_record_by_tnumber(t_number, init_records)
    edit_data = get_record_by_tnumber(t_number, edit_records)
    adjusts = get_record_by_tnumber(t_number, adjust_records)
    
    # Edit the raw data and return the edited version
    edit_data, adjusts = editor(detail, init_data, edit_data, adjusts)

    print(edit_data)
    
    # Write back the edited data
    update_record_by_tnumber(t_number, edit_data, edit_records)
    st.session_state["edit_records"] = edit_records

    # Write back the adjust record
    update_record_by_tnumber(t_number, adjusts, adjust_records)
    st.session_state["adjust_records"] = adjust_records
