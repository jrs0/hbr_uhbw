import numpy as np
from pandas import DataFrame, Series, cut

def ckd(has_index_egfr: DataFrame) -> Series:
    """Calculate the ARC HBR chronic kidney disease (CKD) criterion

    The ARC HBR CKD criterion is calculated based on the eGFR as
    follows:

    | eGFR                           | Score |
    |--------------------------------|-------|
    | eGFR < 30 mL/min               | 1.0   |
    | 30 mL/min \<= eGFR < 60 mL/min | 0.5   |
    | eGFR >= 60 mL/min              | 0.0   |

    If the eGFR is NaN, set score to zero (TODO: fall back to ICD-10
    codes in this case)

    Args:
        has_index_egfr: Dataframe having the column `index_egfr` (in units of mL/min)
            with the eGFR measurement at index, or NaN which means no eGFR
            measurement was found at the index.

    Returns:
        A series containing the CKD ARC criterion, based on the eGFR at
            index.
    """

    # Replace NaN values for now with 100 (meaning score 0.0)
    df = has_index_egfr["index_egfr"].fillna(90)

    # Using a high upper limit to catch any high eGFR values. In practice,
    # the highest value is 90 (which comes from the string ">90" in the database).
    return cut(df, [0, 30, 60, 10000], right=False, labels=[1.0, 0.5, 0.0])


def anaemia(has_index_hb_and_gender: DataFrame) -> Series:
    """Calculate the ARC HBR anaemia (low Hb) criterion

    Calculates anaemia based on the worst (lowest) index Hb measurement
    and gender currently. Should be modified to take most recent Hb value
    or clinical code.

    Args:
        has_index_hb_and_gender: Dataframe having the column `index_hb` containing the
            Hb measurement (g/dL) at the index event, or NaN if no Hb measurement
            was made. Also contains `gender` (categorical with categories "male",
            "female", and "unknown").

    Returns:
        A series containing the HBR score for the index episode.
    """

    df = has_index_hb_and_gender

    # Evaluated in order
    arc_score_conditions = [
        df["index_hb"] < 11.0,  # Major for any gender
        df["index_hb"] < 11.9,  # Minor for any gender
        (df["index_hb"] < 12.9) & (df["gender"] == "male"),  # Minor for male
        df["index_hb"] >= 12.9,  # None for any gender
    ]
    arc_scores = [1.0, 0.5, 0.5, 0.0]

    # Default is used to fill missing Hb score with 0.0 for now. TODO: replace with
    # fall-back to recent Hb, or codes.
    return Series(
        np.select(arc_score_conditions, arc_scores, default=0.0),
        index=df.index,
    )


def tcp(has_index_platelets: DataFrame) -> Series:
    """Calculate the ARC HBR thrombocytopenia (low platelet count) criterion

    The score is 1.0 if platelet count < 100e9/L, otherwise it is 0.0.

    Args:
        has_index_platelets: Has column `index_platelets`, which is the
            platelet count measurement in the index.

    Returns:
        Series containing the ARC score
    """
    return Series(
        np.where(has_index_platelets["index_platelets"] < 100, 1.0, 0),
        index=has_index_platelets.index,
    )
    
    
def prior_bleeding(has_prior_bleeding: DataFrame) -> Series:
    """Calculate the prior bleeding/transfusion ARC HBR criterion

    This function takes a dataframe with a column prior_bleeding_12
    with a count of the prior bleeding events in the previous year.

    TODO: Input needs a separate column for bleeding in 6 months and
    bleeding in a year, so distinguish 0.5 from 1. Also need to add
    transfusion.

    Args:
        has_prior_bleeding: Has a column `prior_bleeding_12` with a count
            of the number of bleeds occurring one year before the index.
            Has `episode_id` as the index.

    Returns:
        The ARC HBR bleeding/transfusion criterion (0.0, 0.5, or 1.0)
    """
    return Series(
        np.where(has_prior_bleeding["prior_bleeding_12"] > 0, 0.5, 0),
        index=has_prior_bleeding.index,
    )