"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine, get_data
from pyhbr.middle import from_hic
from pyhbr.data_source import hic

import pandas as pd

pd.set_option("display.max_rows", 50)

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

codes = from_hic.get_clinical_codes(engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml")
lab_results = from_hic.get_lab_results(engine)
prescriptions = from_hic.get_prescriptions(engine)
demographics = get_data(engine, hic.demographics_query)
episodes = get_data(engine, hic.episodes_query, start_date, end_date)

def index_episodes(episodes: pd.DataFrame, codes: pd.DataFrame) -> pd.DataFrame:
    """Get the index episodes for ACS/PCI patients

    Index episodes are defined by the contents of the first episode of
    the spell (i.e. the cause of admission to hospital). Episodes are
    considered an index event if:

    * The primary diagnosis contains an ACS ICD-10 code; or
    * There is a PCI procedure in any primary or secondary position

    The table returned contains only the episodes that match, along
    with all the information about that episode present in the episodes
    and codes tables.   

    Args:
        episodes: All patient episodes. Must contain `episode_id`, `spell_id`
            and `episode_start`.
        codes: All diagnosis/procedure codes by episode. Must contain
            `episode_id`, `position` (indexed from 1 which is the primary 
            code, >1 are secondary codes), and `group` (containing either `acs` 
            or `pci`).

    Returns:
        The index episodes.
    """

    # Index episodes are defined by the contents of the first episode in the
    # spell (to capture to cause of admission to hospital).
    first_episodes = (
        episodes.sort_values("episode_start").groupby("spell_id").head(1)
    )

    # Join the diagnosis/procedure codes (inner join reduces to episodes which
    # have codes in any group, which is a superset of the index episodes)
    first_episodes_with_codes = (
        pd.merge(first_episodes, codes, how="inner", on="episode_id")
    )

    # ACS matches based on a primary diagnosis of ACS (this is to rule out
    # cases where patient history may contain ACS recorded as a secondary
    # diagnosis).
    acs_match = (
        (first_episodes_with_codes["group"] == "acs_bezin") &
        (first_episodes_with_codes["position"] == 1)
    )

    # A PCI match is allowed anywhere in the procedures list, but must still
    # be present in the index episode
    pci_match = (first_episodes_with_codes["group"] == "pci")

    return first_episodes_with_codes[acs_match | pci_match]