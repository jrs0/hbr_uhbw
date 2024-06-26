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

edit_records = ss["edit_records"]

#edit_records = mock_editor(detail, init_records)

summary_records = summary_data.get_records(init_records, edit_records)
print(summary_records)

init_df = utils.records_to_df(init_records)
summary_df = utils.records_to_df(summary_records)

scores = arc.all_scores(summary_records)

df = summary_df.merge(scores, on="t_number", how="left")

df["arc_total"] = df.filter(regex="score").sum(axis=1)

columns = [
    "age",
    "gender",
    "oac",
    "cancer",
    "nsaid",
    "prior_surgery_trauma",
    "planned_surgery",
    "cirrhosis_ptl_hyp",
    "hb",
    "egfr",
    "platelets",
    "prior_bleeding",
    "prior_ich_stroke",
]

units = {
    "hb": "g/dL",
    "platelets": "×10⁹/L",
    "egfr": "mL/min",
}

# Logic needs to preserve None values
for col in columns:

    df[col] = df[col].astype("object")
    
    for n in range(len(df)):
        edited = df.loc[n, f"{col}_edited"]
        value = df.loc[n, col]
        
        if (value is not None) and not pd.isna(value):
            if col in units:
                value = f"{value} {units[col]}"
            if edited:
                value = f"✎ {value}"

        df.loc[n, col] = value
            
grid_builder = GridOptionsBuilder.from_dataframe(df)

def make_arc_score_styler(arc_field: str) -> JsCode:
    """Create a javascript styler for ARC score cells"""
    return JsCode(
        f"""
        function(params) {{
            if (params.data.{arc_field} < 0.5) {{
                return {{
                    'color': 'green',
                }}
            }} else if (params.data.{arc_field} < 1.0) {{
                return {{
                    'color': 'orange',
                }}
            }} else {{
                return {{
                    'color': 'red',
                }}
            }}
        }};
        """
    )

grid_builder.configure_column(
    field="name",
    pinned="left",
    lockPinned=True,
    headerName="Name",
    headerTooltip="Hover to show T Number",
    tooltipField="t_number",
)

grid_builder.configure_column(
    field="arc_total",
    pinned="left",
    lockPinned=True,
    headerName="ARC Score",
    cellStyle=make_arc_score_styler("arc_score")
)

grid_builder.configure_column(
    field="gender", headerName="Gender"
)

grid_builder.configure_column(
    field="age", headerName="Age", cellStyle=make_arc_score_styler("age_score")
)

grid_builder.configure_column(
    field="oac", headerName="OAC Use", cellStyle=make_arc_score_styler("oac_score")
)

grid_builder.configure_column(
    field="hb", headerName="Hb", cellStyle=make_arc_score_styler("hb_score")
)

grid_builder.configure_column(
    field="platelets", headerName="Platelets", cellStyle=make_arc_score_styler("platelets_score")
)

grid_builder.configure_column(
    field="egfr", headerName="eGFR", cellStyle=make_arc_score_styler("egfr_score")
)

grid_builder.configure_column(
    field="prior_bleeding", headerName="Prior Bleeding", cellStyle=make_arc_score_styler("prior_bleeding_score")
)

grid_builder.configure_column(
    field="cirrhosis_ptl_hyp", headerName="Cirrhosis with portal hypertension", cellStyle=make_arc_score_styler("prior_bleeding_score")
)

grid_builder.configure_column(
    field="nsaid", headerName="NSAID/Steriod Use", cellStyle=make_arc_score_styler("nsaid_score")
)

grid_builder.configure_column(
    field="cancer", headerName="Cancer", cellStyle=make_arc_score_styler("cancer_score")
)

grid_builder.configure_column(
    field="prior_ich_stroke", headerName="Prior ICH/Stroke", cellStyle=make_arc_score_styler("prior_ich_stroke_score")
)

grid_builder.configure_column(
    field="prior_surgery_trauma", headerName="Prior Surgery/Trauma", cellStyle=make_arc_score_styler("prior_surgery_trauma_score")
)

grid_builder.configure_column(
    field="planned_surgery", headerName="Planned Surgery on DAPT", cellStyle=make_arc_score_styler("planned_surgery_score")
)


hidden_cols = [
    col for col in df.columns
    if ("score" in col) or ("edited" in col)]
hidden_cols.append("t_number")

# Hide columns that aren't needed
for col in hidden_cols:
    grid_builder.configure_column(field=col, hide=True)

grid_options = grid_builder.build()
    
# Configure other properties directly
grid_options["tooltipShowDelay"] = 500
grid_options["rowSelection"] = "single"

with summary:
    grid_return = AgGrid(
        df,
        grid_options,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False
    )

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

    edit_record = editor(detail, t_number, arc_total, init_record, edit_record)
    
    edit_records[t_number] = edit_record

    print(edit_record)

ss["edit_records"] = edit_records
    
