"""Calculate the ARC HBR score for the HIC data
"""

import datetime as dt
import matplotlib.pyplot as plt

from pyhbr.common import make_engine
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr
from pyhbr.clinical_codes import counting
from pyhbr.data_source import hic

import importlib

importlib.reload(arc_hbr)
importlib.reload(from_hic)
importlib.reload(hic)
importlib.reload(counting)

import pandas as pd

pd.set_option("display.max_rows", 100)

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

codes = from_hic.get_clinical_codes(
    engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
)  # slow
episodes = from_hic.get_episodes(engine, start_date, end_date)  # fast
prescriptions = from_hic.get_prescriptions(engine, episodes)  # fast
lab_results = from_hic.get_lab_results(engine, episodes)  # really slow
demographics = from_hic.get_demographics(engine)

if episodes.value_counts("episode_id").max() > 1:
    raise RuntimeError(
        "Found non-unique episode IDs; subsequent script will be invalid"
    )

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_episodes = arc_hbr.index_episodes(episodes, codes)

# Get other episodes relative to the index episode (for counting code
# groups before/after the index)
all_other_codes = counting.get_all_other_codes(index_episodes, episodes, codes)

# Get the episodes that occurred in the previous year (for clinical code features)
max_before = dt.timedelta(days=365)
min_before = dt.timedelta(days=30)
previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)

# Get the episodes that occurred in the following year (for clinical code outcomes)
min_after = dt.timedelta(hours=72)  # Exclude periprocedural events
max_after = dt.timedelta(days=365)
following_year = counting.get_time_window(all_other_codes, min_after, max_after)

# Begin a table of general features (more granular than the ARC-HBR criteria,
# from which the ARC score will be computed)
features = pd.DataFrame()
features[["acs_index", "pci_index"]] = index_episodes[["acs_index", "pci_index"]]
features["age"] = arc_hbr.calculate_age(index_episodes, demographics)
features["gender"] = arc_hbr.get_gender(index_episodes, demographics)
features["min_index_egfr"] = arc_hbr.min_index_result("egfr", index_episodes, lab_results)
features["min_index_hb"] = arc_hbr.min_index_result("hb", index_episodes, lab_results)
features["min_index_platelets"] = arc_hbr.min_index_result(
    "platelets", index_episodes, lab_results
)

bleeding_groups = ["bleeding_al_ani"]
features["prior_bleeding_12"] = counting.count_code_groups(
    index_episodes, previous_year, bleeding_groups, False
)
# TODO: transfusion

cancer_groups = ["cancer"]
features["prior_cancer"] = counting.count_code_groups(
    index_episodes, previous_year, cancer_groups, True
)
# TODO: add cancer therapy

# Calculate the ARC HBR score from the more granular features.
arc_hbr_score = arc_hbr.get_arc_hbr_score(features, prescriptions)

# Get the bleeding outcome
bleeding_outcome = counting.count_code_groups(
    index_episodes, following_year, bleeding_groups, True
)

arc_hbr.plot_index_measurement_distribution(features)
plt.show()
