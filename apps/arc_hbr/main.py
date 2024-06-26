import streamlit as st
import pandas as pd
from faker import Faker
from st_aggrid import AgGrid, JsCode, GridOptionsBuilder
import numpy as np
from random import randint, choice
import arc
import utils
import random

st.set_page_config(layout="wide", page_title="ARC HBR Calculator")
st.info(
    "This is a test version of this app, using randomly generated (fake) data, and has no access to patient information.",
    icon="⚠️",
)

seed = 0

fake = Faker(seed=seed)

num_rows = 10


@st.cache_data
def make_data(seed: int) -> pd.DataFrame:

    data = {
        "name": [fake.name() for n in range(num_rows)],
        "t_number": [utils.random_tnumber() for n in range(num_rows)],
        "gender": [utils.random_gender() for n in range(num_rows)],
        "age": [int(x) for x in np.random.normal(70, 10, num_rows)],
        "prior_bleeding_12": [random.choice([0, 1]) for x in range(num_rows)],
        "index_hb": np.random.normal(12, 2, num_rows),
        "index_egfr": [max(x, 0, 0) for x in np.random.normal(60, 50, num_rows)],
        "index_platelets": [max(x, 0, 0) for x in np.random.normal(150, 100, num_rows)],
    }
    return pd.DataFrame(data)


arc_score = make_data(seed=seed)

# Convert some columns to text version
arc_score["hb_text"] = arc_score["index_hb"].apply(lambda x: f"{x:.1f} g/L")

# Convert some columns to text version
arc_score["egfr_text"] = arc_score["index_egfr"].apply(lambda x: f"{x:.1f} mL/min")

# Convert some columns to text version
arc_score["platelets_text"] = arc_score["index_platelets"].apply(
    lambda x: f"{x:.0f} ×10⁹/L"
)

# Convert some columns to text version
arc_score["prior_bleeding_text"] = arc_score["prior_bleeding_12"].map(
    {0: "No", 1: "Yes"}
)

# Calculate arc score for age
arc_score["arc_score_age"] = arc_score["age"].map(lambda x: 0.5 if x >= 75.0 else 0.0)

# Calculate arc score for anaemia
arc_score["arc_score_hb"] = arc.anaemia(arc_score)

# Calculate arc score for chronic kidney disease
arc_score["arc_score_ckd"] = arc.ckd(arc_score)

# Calculate arc score for thrombocytopenia
arc_score["arc_score_tcp"] = arc.tcp(arc_score)

# Calculate arc score for thrombocytopenia
arc_score["arc_score_prior_bleeding"] = arc.prior_bleeding(arc_score)

# Calculate the total ARC score
arc_score.insert(1, "arc_score_total", arc_score.filter(regex="arc_score*").sum(axis=1))

grid_builder = GridOptionsBuilder.from_dataframe(arc_score)

def make_arc_score_styler(arc_field: str) -> JsCode:
    """Create a javascript styler for ARC score cells"""
    return JsCode(
        f"""
        function(params) {{
            if (params.data.{arc_field} < 0.5) {{
                return {{
                    'color': 'black',
                    'backgroundColor': 'lightgreen'
                }}
            }} else if (params.data.{arc_field} < 1.0) {{
                return {{
                    'color': 'white',
                    'backgroundColor': 'orange'
                }}
            }} else {{
                return {{
                    'color': 'white',
                    'backgroundColor': 'orangered'
                }}
            }}
        }};
        """
    )


grid_builder.configure_column(
    field="name",
    headerName="Name",
    headerTooltip="Hover to show T Number",
    tooltipField="t_number",
)
grid_builder.configure_column(
    field="age", headerName="Age", cellStyle=make_arc_score_styler("arc_score_age")
)
grid_builder.configure_column(
    field="arc_score_total",
    headerName="ARC Score",
    cellStyle=make_arc_score_styler("arc_score_total"),
)
grid_builder.configure_column(
    field="hb_text",
    headerName="Haemoglobin",
    cellStyle=make_arc_score_styler("arc_score_hb"),
)
grid_builder.configure_column(
    field="platelets_text",
    headerName="Platelet Count",
    cellStyle=make_arc_score_styler("arc_score_tcp"),
)
grid_builder.configure_column(
    field="egfr_text",
    headerName="eGFR",
    cellStyle=make_arc_score_styler("arc_score_ckd"),
)
grid_builder.configure_column(
    field="prior_bleeding_text",
    headerName="Prior Bleeding",
    cellStyle=make_arc_score_styler("arc_score_prior_bleeding"),
)
grid_builder.configure_column(field="gender", headerName="Gender")

hidden_cols = [
    "arc_score_age",
    "arc_score_hb",
    "arc_score_ckd",
    "arc_score_tcp",
    "arc_score_prior_bleeding",
    "index_hb",
    "index_egfr",
    "index_platelets",
    "prior_bleeding_12",
    "t_number",
]

# Hide columns that aren't needed
for col in hidden_cols:
    grid_builder.configure_column(field=col, hide=True)

grid_options = grid_builder.build()

# Configure other properties directly
grid_options["tooltipShowDelay"] = 500
grid_options["rowSelection"] = "single"

grid_return = AgGrid(arc_score, grid_options, allow_unsafe_jscode=True, enable_enterprise_modules=False)

sel = grid_return.selected_rows
if sel is not None:
    
    if sel["arc_score_total"][0] < 0.5:
        colour = "green"
    elif sel["arc_score_total"][0] < 1.0:
        colour = "orange"
    else:
        colour = "red"
    
    c = st.container(border=True)
    c.header(f"{sel['name'][0]} :{colour}[{sel['arc_score_total'][0]:.1f}]", divider=colour)
    
    cols = c.columns(13)
    
    criteria = {
        "index_hb": "Haemoglobin",
        "index_platelets": "Platelet Count",
        "index_egfr": "eGFR" 
    }
    
    c.write(sel)
