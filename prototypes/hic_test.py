"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine, get_data
from pyhbr.middle import from_hic
from pyhbr.data_source import hic
from pyhbr.analysis import arc_hbr

import pandas as pd

pd.set_option("display.max_rows", 50)

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

codes = from_hic.get_clinical_codes(
    engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
)  # slow
episodes = get_data(engine, hic.episodes_query, start_date, end_date)  # fast
prescriptions = from_hic.get_prescriptions(engine, episodes)  # fast
lab_results = from_hic.get_lab_results(engine, episodes)  # really slow

demographics = get_data(engine, hic.demographics_query)

if episodes.value_counts("episode_id").max() > 1:
    raise RuntimeError(
        "Found non-unique episode IDs; subsequent script will be invalid"
    )

index_episodes = arc_hbr.index_episodes(episodes, codes)
