# How do outcomes and management depend on frailty.

import importlib
import datetime as dt
from dateutil import parser

import pandas as pd
from pyhbr import common, clinical_codes
from pyhbr.analysis import acs
from pyhbr.clinical_codes import counting
from pyhbr.data_source import icb, hic_icb, hic
from pyhbr.middle import from_icb, from_hic
from pyhbr.analysis import arc_hbr
import yaml
from pandas import DataFrame

importlib.reload(common)
importlib.reload(acs)
importlib.reload(from_icb)
importlib.reload(from_hic)
importlib.reload(icb)
importlib.reload(hic)
importlib.reload(hic_icb)
importlib.reload(clinical_codes)
importlib.reload(counting)

# Read the configuration file
with open("scripts/frailty.yaml") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(f"Failed to load config file: {exc}")
        exit(1)


# Set a date range for episode fetch. The primary
# care data start in Oct 2019. Use an end date
# in the future to ensure all recent data is fetched.
# Index spell data is limited based on the min/max
# dates seen in all the datasets below.
start_date = parser.parse(config["start_date"])
end_date = parser.parse(config["end_date"])

# Get the raw HES data (this takes a long time ~ 20 minutes, up to 2 hours
# at UHBW).
abi_engine = common.make_engine(database="abi")
raw_sus_data = from_icb.get_raw_sus_data(abi_engine, start_date, end_date)

# Note that the SUS data is limited to in-area patients only, so that
# the patients are present in the primary care attributes table (see
# the notes on valid commissioner code in icb.py). This restriction
# can be lifted if the primary care data is not used in the analysis.

# The full dataset is large, so using a save point
# to speed up script development
common.save_item(raw_sus_data, "raw_sus_data")
raw_sus_data, raw_sus_data_path = common.load_item("raw_sus_data")

# Read the code groups and reduce to a table. The remainder of the code
# uses the code groups dataframe, which you can either get from the code
# files (as is done here) or create them manually
diagnosis_codes = clinical_codes.load_from_package(config["icd10_codes_file"])
procedure_codes = clinical_codes.load_from_package(config["opcs4_codes_file"])
code_groups = clinical_codes.get_code_groups(diagnosis_codes, procedure_codes)

# HES data + demographics
episodes, codes = from_icb.get_episodes_and_codes(raw_sus_data, code_groups)

# Get the index episodes (primary diagnosis ICD-10 ACS only)
# Modify the code groups used to define the index event here.
index_spells = acs.get_index_spells(
    episodes,
    codes,
    config["acs_index_code_group"],
    None,  # Do not include an episode based on PCI
    config["stemi_index_code_group"],
    config["nstemi_index_code_group"],
)

# Count the amount of STEMI/NSTEMI
stemi_count = index_spells["stemi_index"].sum()
nstemi_count = index_spells["nstemi_index"].sum()

# Check these two groups are disjoint (expected)
if (index_spells["stemi_index"] & index_spells["nstemi_index"]).sum() > 0:
    raise RuntimeError("Invalid overlap of STEMI/NSTEMI index events")

# Now it is known that STEMI/NSTEMI are disjoint, remainder is unstable angina
unstable_angina_count = len(index_spells) - stemi_count - nstemi_count

# Print the proportions
print(f"STEMI: {100*stemi_count/len(index_spells):.2f}%")
print(f"NSTEMI: {100*nstemi_count/len(index_spells):.2f}%")
print(f"Unstable angina: {100*unstable_angina_count/len(index_spells):.2f}%")

# The next step is to determine management, which is one of PCI, CABG,
# or conservatively managed (meaning medication only, but manifesting
# as ACS index with neither PCI nor CABG). To do this, get all the other
# codes and

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(index_spells, episodes, codes)

# Choose a window for identifying management
min_after = dt.timedelta(hours=0)
max_after = dt.timedelta(days=7)
management_window = counting.get_time_window(all_other_codes, min_after, max_after)

# Ensure that rows are only kept if they are from the same spell (management
# must occur before a hospital discharge and readmission)
same_spell_management_window = management_window[
    management_window["index_spell_id"].eq(management_window["other_spell_id"])
]


def has_management(window: DataFrame, group: str, name: str) -> DataFrame:
    return (
        window.groupby("index_spell_id")[["group"]]
        .agg(lambda g: g.eq(group).any())
        .rename(columns={"group": name})
    )


# Find which management was performed
has_cabg = has_management(same_spell_management_window, "cabg_bortolussi", "cabg")
has_pci = has_management(same_spell_management_window, "all_pci_pathak", "pci")
index_spells = index_spells.merge(
    has_cabg, left_index=True, right_index=True, how="left"
).merge(has_pci, left_index=True, right_index=True, how="left")

# Check the proportions of different types of management
pci_prop = index_spells["pci"].sum() / len(index_spells)
cabg_prop = index_spells["cabg"].sum() / len(index_spells)
conservative_prop = 1 - pci_prop - cabg_prop
print(f"Of {len(index_spells)} ACS patients, {100*pci_prop:.2f}% had PCI, {100*cabg_prop:.2f}% had CABG, and {100*conservative_prop:.2f}% were conservatively managed")

# Get date of death and cause of death from registry data
date_of_death, cause_of_death = from_icb.get_mortality(
    abi_engine, start_date, end_date, code_groups
)

# Get follow-up window for defining non-fatal outcomes
min_after = dt.timedelta(hours=48)
max_after = dt.timedelta(days=365)
following_year = counting.get_time_window(all_other_codes, min_after, max_after)

# Get the non-fatal ischaemia outcomes. Allowing
# outcomes from the index spell considerably
# increases the ischaemia rate to about 25%, which
# seems too high to be reasonable. This could be
# due to (e.g.) a majority of ACS patients having two
# acute episodes to treat the index event. Excluding
# the index event brings the prevalence down to around 6%,
# more in line with published research. Allowing
# secondary codes somewhat increases the number of outcomes.
max_position = config["outcomes"]["ischaemia"]["non_fatal"]["max_position"]
exclude_index_spell = True
non_fatal_ischaemia_group = config["outcomes"]["ischaemia"]["non_fatal"]["group"]
non_fatal_ischaemia = acs.filter_by_code_groups(
    following_year,
    non_fatal_ischaemia_group,
    max_position,
    exclude_index_spell,
)

# Get the fatal ischaemia outcomes. 
fatal_ischaemia_group = config["outcomes"]["ischaemia"]["fatal"]["group"]
max_position = config["outcomes"]["ischaemia"]["fatal"]["max_position"]
fatal_ischaemia = acs.identify_fatal_outcome(
    index_spells,
    date_of_death,
    cause_of_death,
    fatal_ischaemia_group,
    max_position,
    max_after,
)

# Count the non-fatal bleeding/ischaemia outcomes
outcomes = pd.DataFrame()
outcomes["non_fatal_ischaemia"] = counting.count_code_groups(
    index_spells, non_fatal_ischaemia
)
outcomes["fatal_ischaemia"] = counting.count_code_groups(index_spells, fatal_ischaemia)

# Get the survival time and right censoring data for bleeding and ischaemia (combines
# both fatal/non-fatal outcomes with a flag to distinguish which is which)
ischaemia_survival = acs.get_survival_data(index_spells, fatal_ischaemia, non_fatal_ischaemia, max_after)

# Reduce the outcomes to boolean, and make aggregate
# (fatal/non-fatal) columns
bool_outcomes = outcomes > 0
bool_outcomes["ischaemia"] = (
    bool_outcomes["fatal_ischaemia"] | bool_outcomes["non_fatal_ischaemia"]
)

# Quick check on prevalences
100 * bool_outcomes.sum() / len(bool_outcomes)

# Get hic index features (drop instead of keep in case new
# features are added)
features_index = index_spells.drop(columns=["episode_id", "patient_id", "spell_start"])

# Combine all tables (features and outcomes) into a single table
# for saving.
data = {
    # Outcomes
    "outcomes": bool_outcomes,
    "non_fatal_ischaemia": non_fatal_ischaemia,
    "fatal_ischaemia": fatal_ischaemia,
    "ischaemia_survival": ischaemia_survival,
    "features_index": features_index,
}

common.save_item(data, f"{config['analysis_name']}_data")
