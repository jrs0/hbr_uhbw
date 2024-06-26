import sys
import utils

def scores(edit_data: dict[str, str | int | float | None]) -> dict[str, float]:
    """Return a dictionary of the ARC score for each criterion
    """

    this_module = sys.modules[__name__]
        
    criteria = [
        "age",
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

    scores = {}
    for criterion in criteria:
        calc = getattr(this_module, f"{criterion}_score")
        scores[f"{criterion}_score"] = calc(edit_data)

    return scores

def all_scores(records: dict[str, [dict[str, str | int | float | None]]]):
    """Calculate ARC score data for all patients, as a dataframe
    """

    score_records = {}
    for t_number, record in records.items():
        score_record = scores(record)
        score_records[t_number] = score_record

    return utils.records_to_df(score_records)

def age_score(data) -> float | None:
    if data["age"] is None:
        return None
    elif data["age"] < 75:
        return 0.0
    else: 
        return 0.5

def oac_score(data) -> float | None:
    if data["oac"] is None:
        return None
    elif data["oac"] == "Yes":
        return 1.0
    else: 
        return 0.0

def cancer_score(data) -> float | None:
    if data["cancer"] is None:
        return None
    elif data["cancer"] == "Yes":
        return 1.0
    else: 
        return 0.0
    
def nsaid_score(data) -> float | None:
    if data["nsaid"] is None:
        return None
    elif data["nsaid"] == "Yes":
        return 0.5
    else: 
        return 0.0

def prior_surgery_trauma_score(data) -> float | None:
    if data["prior_surgery_trauma"] is None:
        return None
    elif data["prior_surgery_trauma"] == "Yes":
        return 1.0
    else: 
        return 0.0

def planned_surgery_score(data) -> float | None:
    if data["planned_surgery"] is None:
        return None
    elif data["planned_surgery"] == "Yes":
        return 1.0
    else: 
        return 0.0
    
def cirrhosis_ptl_hyp_score(data) -> float | None:
    if data["cirrhosis_ptl_hyp"] is None:
        return None
    elif data["cirrhosis_ptl_hyp"] == "Yes":
        return 1.0
    else: 
        return 0.0
    
def hb_score(data) -> float | None:
    """Anaemia score
    """
    hb = data["hb"]
    gender = data["gender"]

    # Need to handle gender None
    if hb is None:
        return None
    elif hb < 11.0: # Major for any gender
        return 1.0 
    elif hb < 11.9: # Minor for any gender
        return 0.5
    elif (hb < 12.9) and (gender == "Male"):
        return 0.5
    else:
        return 0.0

def egfr_score(data) -> float | None:
    """Renal function score
    """
    egfr = data["egfr"]

    if egfr is None:
        return None
    elif egfr < 30.0:
        return 1.0 
    elif egfr < 60.0:
        return 0.5
    else:
        return 0.0
    
def platelets_score(data) -> float | None:
    """Thrombocytopenia score
    """
    if data["platelets"] is None:
        return None
    elif data["platelets"] < 100:
        return 1.0
    else: 
        return 0.0

def prior_bleeding_score(data) -> float | None:
    if data["prior_bleeding"] is None:
        return None
    elif data["prior_bleeding"] == "< 6 months or recurrent":
        return 1.0
    elif data["prior_bleeding"] == "< 12 months":
        return 0.5
    else:
        return 0.0

def prior_ich_stroke_score(data) -> float | None:
    if data["prior_ich_stroke"] is None:
        return None
    elif data["prior_ich_stroke"] == "bAVM, ICH, or moderate/severe ischaemic stroke < 6 months":
        return 1.0
    elif data["prior_ich_stroke"] == "Any prior ischaemic stroke":
        return 0.5
    else:
        return 0.0
