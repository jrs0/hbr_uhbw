import numpy as np
from random import randint, choice

def random_arc_score() -> float:
    return randint(0, 2) / 2.0

def random_gender() -> str:
    return choice(["M", "F"])

def random_tnumber() -> str:
    """T followed by 7 digits"""
    num = randint(0, 9999999)
    return f"T{num:>07}"