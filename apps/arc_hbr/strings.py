import arc
import sys

def score_to_colour(score: float | None) -> str | None:
    if score is None:
        return None
    elif score < 0.5:
        return "green"
    elif score < 1.0:
        return "orange"
    else:
        return "red"

def age_string(data) -> str:
    if data["age"] is None:
        return f":grey[missing]"
    else:
        score = arc.age_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['age']}]"

def oac_string(data) -> str:
    if data["oac"] is None:
        return f":grey[missing]"
    else:
        score = arc.oac_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['oac']}]"

def prior_surgery_trauma_string(data) -> str:
    if data["prior_surgery_trauma"] is None:
        return f":grey[missing]"
    else:
        score = arc.prior_surgery_trauma_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['prior_surgery_trauma']}]"

def planned_surgery_string(data) -> str:
    if data["planned_surgery"] is None:
        return f":grey[missing]"
    else:
        score = arc.planned_surgery_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['planned_surgery']}]"
    
def cancer_string(data) -> str:
    if data["cancer"] is None:
        return f":grey[missing]"
    else:
        score = arc.cancer_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['cancer']}]"
    
def nsaid_string(data) -> str:
    if data["nsaid"] is None:
        return f":grey[missing]"
    else:
        score = arc.nsaid_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['nsaid']}]"
    
def gender_string(data) -> str:
    if data["gender"] is None:
        return f":grey[missing]"
    else:
        return data["gender"]

def hb_string(data) -> str:
    if data["hb"] is None:
        return f":grey[missing]"
    else:
        score = arc.hb_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['hb']:.1f} g/dL]"

def egfr_string(data) -> str:
    if data["egfr"] is None:
        return f":grey[missing]"
    else:
        score = arc.egfr_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['egfr']:.1f} mL/min]"
    
def platelets_string(data) -> str:
    if data["platelets"] is None:
        return f":grey[missing]"
    else:
        score = arc.platelets_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['platelets']:.1f} ×10⁹/L]"

def prior_bleeding_string(data) -> str:
    if data["prior_bleeding"] is None:
        return f":grey[missing]"
    else:
        score = arc.prior_bleeding_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['prior_bleeding']}]"

def prior_ich_stroke_string(data) -> str:
    if data["prior_ich_stroke"] is None:
        return f":grey[missing]"
    else:
        score = arc.prior_ich_stroke_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['prior_ich_stroke']}]"
    
def cirrhosis_ptl_hyp_string(data) -> str:
    if data["cirrhosis_ptl_hyp"] is None:
        return f":grey[missing]"
    else:
        score = arc.cirrhosis_ptl_hyp_score(data)
        colour = score_to_colour(score)
        return f":{colour}[{data['cirrhosis_ptl_hyp']}]"
