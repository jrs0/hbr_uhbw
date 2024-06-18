"""Calculate the ARC HBR score for the HIC data
"""

import datetime as dt
import matplotlib.pyplot as plt

from pyhbr import common
from pyhbr.middle import from_hic
from pyhbr.analysis import arc_hbr
from pyhbr.analysis import acs
from pyhbr.clinical_codes import counting
from pyhbr.data_source import hic

import importlib

importlib.reload(common)
importlib.reload(arc_hbr)
importlib.reload(from_hic)
importlib.reload(hic)
importlib.reload(counting)
importlib.reload(acs)

import pandas as pd

pd.set_option("display.max_rows", 100)

# Set a date range for episode fetch
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

# Fetch data
engine = common.make_engine()
codes = from_hic.get_clinical_codes(
    engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
)  # slow
episodes = from_hic.get_episodes(engine, start_date, end_date)  # fast
prescriptions = from_hic.get_prescriptions(engine, episodes)  # fast
lab_results = from_hic.get_lab_results(engine, episodes)  # really slow

# Get the index episodes (primary ACS or PCI anywhere in first episode)
index_spells = acs.get_index_spells(
    episodes,
    codes,
    "acs_bezin",
    "all_pci_pathak",
)


# Get other episodes relative to the index episode (for counting code
# groups before/after the index)
all_other_codes = counting.get_all_other_codes(index_spells, episodes, codes)

# Get the episodes that occurred in the previous year (for clinical code features)
max_before = dt.timedelta(days=365)
min_before = dt.timedelta(days=30)
previous_year = counting.get_time_window(all_other_codes, -max_before, -min_before)

# Get the episodes that occurred in the following year (for clinical code outcomes)
min_after = dt.timedelta(hours=72)  # Exclude periprocedural events
max_after = dt.timedelta(days=365)
following_year = counting.get_time_window(all_other_codes, min_after, max_after)

# Calculate more granular features as an intermediate step for calculating the
# ARC HBR score.
features = arc_hbr.first_index_lab_result(index_spells, lab_results, episodes)


def prior_codes(group: str) -> pd.Series:
    """Get the prior codes for this code group

    Note: uses variables in this environment.
    """
    filter = acs.filter_by_code_groups(
        previous_year,
        group,
        999,
        True,
    )
    return counting.count_code_groups(index_spells, filter)


features["prior_bleeding_12"] = prior_codes("bleeding_adaptt")
features["prior_cirrhosis"] = prior_codes("cirrhosis")
features["prior_portal_hyp"] = prior_codes("portal_hypertension")
features["prior_bavm"] = prior_codes("bavm")
features["prior_ich"] = prior_codes("ich")
features["prior_bavm_ich"] = features["prior_bavm"] + features["prior_ich"]
features["prior_ischaemic_stroke"] = prior_codes("ischaemic_stroke")
features["prior_cancer"] = prior_codes("ischaemic_cancer")

# Calculate the ARC HBR score from the more granular features.
arc_hbr_score = pd.DataFrame(index=features.index)
arc_hbr_score["arc_hbr_age"] = arc_hbr.arc_hbr_age(features)
arc_hbr_score["arc_hbr_oac"] = arc_hbr.arc_hbr_medicine(
    index_spells,
    episodes,
    prescriptions,
    "oac",
    1.0,
)
arc_hbr_score["arc_hbr_oac"].sum()
arc_hbr_score["arc_hbr_nsaid"] = arc_hbr.arc_hbr_medicine(
    index_spells,
    episodes,
    prescriptions,
    "nsaid",
    1.0,
)
arc_hbr_score["arc_hbr_nsaid"].sum()
arc_hbr_score["arc_hbr_ckd"] = arc_hbr.arc_hbr_ckd(features)
arc_hbr_score["arc_hbr_anaemia"] = arc_hbr.arc_hbr_anaemia(features)
arc_hbr_score["arc_hbr_tcp"] = arc_hbr.arc_hbr_tcp(features)
arc_hbr_score["arc_hbr_prior_bleeding"] = arc_hbr.arc_hbr_prior_bleeding(features)
arc_hbr_score["arc_hbr_cirrhosis_portal_hyp"] = arc_hbr.arc_hbr_cirrhosis_ptl_hyp(
    features
)
arc_hbr_score["arc_hbr_stroke_ich"] = arc_hbr.arc_hbr_ischaemic_stroke_ich(features)
arc_hbr_score["arc_hbr_cancer"] = arc_hbr.arc_hbr_cancer(features)

# The bleeding outcome is defined by the ADAPTT trial bleeding code group,
# which matches BARC 2-5 bleeding events. Ischaemia outcomes are defined using
# a three-point MACE specifically targetting ischaemic outcomes (i.e. only
# ischaemic stroke is included, rather than haemorrhagic stroke which is sometimes
# included in MACE definitions).

# Get the non-fatal bleeding outcomes
# Excluding the index spells appears to have very
# little effect on the prevalence, so the index spell
# is excluded to be consistent with ischaemia outcome
# definition. Increasing maximum code position increases
# the bleeding rate, but 1 is chosen to restrict to cases
# where bleeding code is not historical/minor.
max_position = 1
exclude_index_spell = True
non_fatal_bleeding_group = "bleeding_adaptt"
non_fatal_bleeding = acs.filter_by_code_groups(
    following_year,
    non_fatal_bleeding_group,
    max_position,
    exclude_index_spell,
)
bleeding_outcome = non_fatal_bleeding

# Get the bleed episodes (for chart review) -- bleeding in any position
groups = following_year[following_year["group"].isin(bleeding_groups)].groupby(
    "base_episode_id"
)
for key, _ in groups:
    print(groups.get_group(key), "\n\n")

arc_hbr.plot_index_measurement_distribution(features)
plt.show()

arc_hbr.plot_arc_score_distribution(arc_hbr_score)
plt.show()

arc_hbr.plot_prescriptions_distribution(episodes, prescriptions)
plt.show()

# Package the data up for saving
data = {
    "episodes": episodes,
    "codes": codes,
    "prescriptions": prescriptions,
    "lab_results": lab_results,
    "index_episodes": index_episodes,
    "features": features,
    "arc_hbr_score": arc_hbr_score,
    "bleeding_outcome": bleeding_outcome,
}

common.save_item(data, "arc_hbr_data")
