import numpy as np
from random import randint, choice
import base64
import streamlit as st

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
