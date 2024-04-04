"""Convert the ICB data to ACS/bleeding/ischaemia datasets

This codes does more preprocessing of the ICB datasets (mainly
the primary care attributes), and packages them up into a training
set.
"""

import importlib
import datetime as dt
import numpy as np
from pyhbr import common
from pyhbr.clinical_codes import counting
from pyhbr.analysis import describe
from pyhbr.analysis import acs
from pyhbr.middle import from_icb

importlib.reload(counting)
importlib.reload(acs)
importlib.reload(describe)
importlib.reload(from_icb)

data = common.load_item("icb_basic_data")

primary_care_attributes = data["primary_care_attributes"]

# Preprocess columns
primary_care_attributes["smoking"] = from_icb.preprocess_smoking(
    primary_care_attributes["smoking"]
)
primary_care_attributes["ethnicity"] = from_icb.preprocess_ethnicity(
    primary_care_attributes["ethnicity"]
)

# Reduce the index spells to those which have a valid row of
# patient attributes
index_spells = data["index_spells"]

swd_index_spells = acs.get_swd_index_spells(index_spells, primary_care_attributes)

# Get the patient index-spell attributes (before reducing based on missingness/low-variance)
all_index_attributes = acs.get_index_attributes(
    swd_index_spells, primary_care_attributes
)

# Remove attribute columns that have too much missingness or where
# the column is nearly constant (low variance)
index_attributes = acs.remove_features(
    all_index_attributes, max_missingness=0.75, const_threshold=0.95
)

# Get other episodes relative to the index episode (for counting code
# groups before/after the index).
all_other_codes = counting.get_all_other_codes(swd_index_spells, data)

# Get the bleeding and ischaemia outcomes
outcomes = acs.get_outcomes(swd_index_spells, all_other_codes)
code_features = acs.get_code_features(swd_index_spells, all_other_codes)

# Process prescriptions
primary_care_prescriptions = data["primary_care_prescriptions"]

# NOTE: converted date column to datetime upstream, but
# need to rerun data fetch script.
primary_care_prescriptions["date"] = pd.to_datetime(primary_care_prescriptions["date"])

# Get counts of relevant prescriptions in the year before the index
prior_prescriptions = acs.prescriptions_before_index(
    swd_index_spells, primary_care_prescriptions
)

primary_care_measurements = data["primary_care_measurements"]


def blood_pressure(
    swd_index_spells: DataFrame, primary_care_measurements: DataFrame
) -> DataFrame:
    """Get recent blood pressure readings

    Args:
        primary_care_measurements: Contains a `name` column containing
            the measurement name (expected to contain "blood_pressure"),
            a `result` column with the format "systolic/diastolic" for
            the blood pressure rows, a `date`, and a `patient_id`.
        swd_index_spells: Has Pandas index `spell_id`, and columns
            `patient_id` and `spell_start`.

    Returns:
        A dataframe index by `spell_id` containing `bp_systolic`
            and `bp_diastolic` columns.
    """

    df = primary_care_measurements

    # Drop rows where the measurement is not known
    df = df[~df["name"].isna()]

    # Drop rows where the prescription date is not known
    df = df[~df["date"].isna()]

    blood_pressure = df[df.name.str.contains("blood_pressure")][
        ["patient_id", "date", "result"]
    ].copy()
    blood_pressure[["bp_systolic", "bp_diastolic"]] = (
        df["result"].str.split("/", expand=True).apply(pd.to_numeric, errors="coerce")
    )

    # Join the prescriptions to the index spells
    df = (
        swd_index_spells[["spell_start", "patient_id"]]
        .reset_index()
        .merge(blood_pressure, how="left", on="patient_id")
    )
    df["time_to_index_spell"] = df["spell_start"] - df["date"]

    # Only keep measurements occurring in the year before the index event
    min_before = dt.timedelta(days=0)
    max_before = dt.timedelta(days=60)
    bp_before_index = counting.get_time_window(
        df, -max_before, -min_before, "time_to_index_spell"
    )

    most_recent_bp = bp_before_index.sort_values("date").groupby("spell_id").tail(1)
    prior_bp = swd_index_spells.merge(
        most_recent_bp, how="left", on="spell_id"
    ).set_index("spell_id")[["bp_systolic", "bp_diastolic"]]

    return prior_bp


prior_blood_pressure = blood_pressure(swd_index_spells, primary_care_measurements)

def hba1c(
    swd_index_spells: DataFrame, primary_care_measurements: DataFrame
) -> DataFrame:
    """Get recent HbA1c from the primary care measurements

    Args:
        primary_care_measurements: Contains a `name` column containing
            the measurement name (expected to contain "blood_pressure"),
            a `result` column with the format "systolic/diastolic" for
            the blood pressure rows, a `date`, and a `patient_id`.
        swd_index_spells: Has Pandas index `spell_id`, and columns
            `patient_id` and `spell_start`.

    Returns:
        A dataframe indexed by `spell_id` containing recent (within 2 months)
            HbA1c values.
    """

    df = primary_care_measurements

    # Drop rows where the measurement is not known
    df = df[~df["name"].isna()]

    # Drop rows where the prescription date is not known
    df = df[~df["date"].isna()]

    hba1c = df[df.name.str.contains("hba1c")][
        ["patient_id", "date", "result"]
    ].copy()
    hba1c["hba1c"] = pd.to_numeric(hba1c["result"], errors="coerce")

    # Join the prescriptions to the index spells
    df = (
        swd_index_spells[["spell_start", "patient_id"]]
        .reset_index()
        .merge(hba1c, how="left", on="patient_id")
    )
    df["time_to_index_spell"] = df["spell_start"] - df["date"]

    # Only keep measurements occurring in the year before the index event
    min_before = dt.timedelta(days=0)
    max_before = dt.timedelta(days=60)
    hba1c_before_index = counting.get_time_window(
        df, -max_before, -min_before, "time_to_index_spell"
    )

    most_recent_hba1c = hba1c_before_index.sort_values("date").groupby("spell_id").tail(1)
    prior_hba1c = swd_index_spells.merge(
        most_recent_hba1c, how="left", on="spell_id"
    ).set_index("spell_id")[["hba1c"]]

    return prior_hba1c

prior_hba1c = hba1c(swd_index_spells, primary_care_measurements)

# Combine all tables (features and outcomes) into a single table
# for saving.
training_data = (
    swd_index_spells[["acs_index", "pci_index"]]
    .merge(outcomes, how="left", on="spell_id")
    .merge(code_features, how="left", on="spell_id")
    .merge(index_attributes, how="left", on="spell_id")
)


rate_summaries = describe.get_column_rates(
    training_data.select_dtypes(include="number")
)
