import numpy as np
from random import randint, choice
import base64
import streamlit as st
import pandas as pd

def random_arc_score() -> float:
    return randint(0, 2) / 2.0

def random_gender() -> str:
    return choice(["M", "F"])

def random_tnumber() -> str:
    """T followed by 7 digits"""
    num = randint(0, 9999999)
    return f"T{num:>07}"

def write_svg(container, path_to_svg: str):
    """Render an SVG to a streamlit container
    
    """
    with open(path_to_svg, mode="rb") as svg:
        b64 = base64.b64encode(svg.read()).decode("utf-8")
        html = fr'<img src="data:image/svg+xml;base64,{b64}"/>'
        container.write(html, unsafe_allow_html=True)

def records_to_df(records):
    """Convert records to dataframe

    Here, a record is a dictionary mapping the value of the
    index column to a row (this is not the same as the
    Pandas records, which is a list of rows)
    """

    pandas_records = [
        record | {"t_number": t_number }
        for t_number, record in records.items()
    ]
    df = pd.DataFrame.from_records(pandas_records)
    return df

def df_to_records(df):
    """Convert dataframe back top records

    Here, a record is a dictionary mapping the value of the
    index column to a row (this is not the same as the
    Pandas records, which is a list of rows)
    """
    pandas_records = df.to_dict("records")
    
    records = {}
    for pandas_record in pandas_records:
        t_number = pandas_record["t_number"]
        
        del pandas_record["t_number"]

        records[t_number] = pandas_record

    return records

def get_empty_edit_records(init_records):    
    """Create empty edit data
    """
    return {
        t_number: {
            key: None for key in record.keys()
        }
        for t_number, record in init_records.items()
    }
