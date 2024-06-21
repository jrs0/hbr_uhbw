import streamlit as st
import pandas as pd
from faker import Faker
from st_aggrid import AgGrid, JsCode, GridOptionsBuilder
import numpy as np
from random import randint

def random_tnumber():
    num = randint(0, 9999999)
    return f"T{num:>07}"

fake = Faker()
data = {
    "Name": [fake.name() for n in range(2)],
    "T Number": [random_tnumber() for n in range(2)],
    "ARC Score": [1, 0],
    "Age": [int(x) for x in np.random.normal(70, 10, 2)],
}
arc_score = pd.DataFrame(data)

grid_builder = GridOptionsBuilder.from_dataframe(arc_score)
grid_builder.configure_column(field="Name", headerTooltip="Hover to show T Number", tooltipField="T Number")

grid_options = grid_builder.build()

# Configure other properties directly
grid_options["tooltipShowDelay"] = 500

print(grid_options)

AgGrid(arc_score, grid_options, allow_unsafe_jscode=True)