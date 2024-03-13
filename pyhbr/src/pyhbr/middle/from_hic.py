"""Convert HIC tables into the formats required for analysis
"""

import pandas as pd
from sqlalchemy import Engine
from pyhbr.clinical_codes import (
    ClinicalCodeTree,
    codes_in_any_group,
    normalise_code,
    load_from_package,
)
from pyhbr.common import get_data
from pyhbr.data_source import hic
from datetime import date, timedelta


def filter_to_groups(
    codes_table: pd.DataFrame, codes: ClinicalCodeTree
) -> pd.DataFrame:
    """Filter a table of raw clinical codes to only keep codes in groups

    Use this function to drop clinical codes which are not of interest,
    and convert all codes to normalised form (lowercase, no whitespace, no dot).

    This function is tested on the HIC dataset, but should be modifiable
    for use with any data source returning diagnoses and procedures as
    separate tables in long format. Consider modifying the columns of
    codes_table that are contained in the output.

    Args:
        codes_table: Either a diagnoses or procedures table. For this
            function to work, it needs:

            * A `code` column containing the clinical code.
            * An `episode_id` identifying which episode contains the code.
            * A `position` identifying the primary/secondary position of the
                code in the episode.

        codes: The clinical codes object (previously loaded from a file)
            containing code groups to use.

    Returns:
        A table containing the episode ID, the clinical code (normalised),
        the group containing the code, and the code position.

    """
    codes_with_groups = codes_in_any_group(codes)
    codes_table["code"] = codes_table["code"].apply(normalise_code)
    codes_table = pd.merge(codes_table, codes_with_groups, on="code", how="inner")
    codes_table = codes_table[["episode_id", "code", "group", "position"]]

    return codes_table


def get_clinical_codes(
    engine: Engine, diagnoses_file: str, procedures_file: str
) -> pd.DataFrame:
    """Main diagnoses/procedures fetch for the HIC data

    This function wraps the diagnoses/procedures queries and a filtering
    operation to reduce the tables to only those rows which contain a code
    in a group. One table is returned which contains both the diagnoses and
    procedures in long format, along with the associated episode ID and the
    primary/secondary position of the code in the episode.

    Args:
        engine: The connection to the database
        diagnoses_file: The diagnoses codes file name (loaded from the package)
        procedures_file: The procedures codes file name (loaded from the package)

    Returns:
        A table containing diagnoses/procedures, normalised codes, code groups,
            diagnosis positions, and associated episode ID.
    """

    diagnosis_codes = load_from_package(diagnoses_file)
    procedures_codes = load_from_package(procedures_file)

    # Fetch the data from the server
    diagnoses = get_data(engine, hic.diagnoses_query)
    procedures = get_data(engine, hic.procedures_query)

    # Reduce data to only code groups, and combine diagnoses/procedures
    filtered_diagnoses = filter_to_groups(diagnoses, diagnosis_codes)
    filtered_procedures = filter_to_groups(procedures, procedures_codes)

    # Tag the diagnoses/procedures, and combine the tables
    filtered_diagnoses["type"] = "diagnosis"
    filtered_procedures["type"] = "procedure"
    
    codes =  pd.concat([filtered_diagnoses, filtered_procedures])
    codes["type"] = codes["type"].astype("category")
    
    return codes


def check_const_column(df: pd.DataFrame, col_name: str, expect: str):
    """Raise an error if a column is not constant

    Args:
        df: The table to check
        col_name: The name of the column which should be constant
        expect: The expected constant value of the column

    Raises:
        RuntimeError: Raised if the column is not constant with
            the expected value.
    """
    if not all(df[col_name] == expect):
        raise RuntimeError(
            f"Found unexpected value in '{col_name}' column. "
            f"Expected constant '{expect}', but got: "
            f"{df[col_name].unique()}"
        )


def get_unlinked_lab_results(engine: Engine) -> pd.DataFrame:
    """Get laboratory results from the HIC database (unlinked to episode)

    This function returns data for the following three
    tests, identified by one of these values in the
    `test_name` column:

    * `hb`: haemoglobin (unit: g/dL)
    * `egfr`: eGFR (unit: mL/min)
    * `platelets`: platelet count (unit: 10^9/L)

    The test result is associated to a `patient_id`,
    and the time when the sample for the test was collected
    is stored in the `sample_date` column.

    Some values in the underlying table contain inequalities
    in the results column, which have been removed (so
    egfr >90 becomes 90).

    Args:
        engine: The connection to the database

    Returns:
        Table of laboratory results, including Hb (haemoglobin),
            platelet count, and eGFR (kidney function). The columns are
            `patient_id`, `test_name`, and `sample_date`.

    """
    df = get_data(engine, hic.pathology_blood_query, ["OBR_BLS_UE", "OBR_BLS_FB"])

    df["test_name"] = df["investigation"] + "_" + df["test"]

    test_of_interest = {
        "OBR_BLS_FB_OBX_BLS_HB": "hb",
        "OBR_BLS_UE_OBX_BLS_EP": "egfr",
        "OBR_BLS_FB_OBX_BLS_PL": "platelets",
    }

    # Only keep tests of interest: platelets, egfr, and hb
    df = df[df["test_name"].isin(test_of_interest.keys())]

    # Rename the items
    df["test_name"] = df["test_name"].map(test_of_interest)

    # Check egfr unit
    rows = df[df["test_name"] == "egfr"]
    check_const_column(rows, "unit", "mL/min")

    # Check hb unit
    rows = df[df["test_name"] == "hb"]
    check_const_column(rows, "unit", "g/L")

    # Check platelets unit (note 10*9/L is not a typo)
    rows = df[df["test_name"] == "platelets"]
    check_const_column(rows, "unit", "10*9/L")

    # Some values include an inequality; e.g.:
    # - egfr: >90
    # - platelets: <3
    #
    # Remove instances of < or > to enable conversion
    # to float.
    df["result"] = df["result"].str.replace("<|>", "", regex=True)

    # Convert results column to float
    df["result"] = df["result"].astype(float)

    # Convert hb units to g/dL (to match ARC HBR definition)
    df.loc[df["test_name"] == "hb", "result"] /= 10.0

    return df[["patient_id", "sample_date", "test_name", "result"]]

def get_unlinked_prescriptions(engine: Engine) -> pd.DataFrame:
    """Get relevant prescriptions from the HIC data (unlinked to episode)

    This function is tailored towards the calculation of the
    ARC HBR score, so it focusses on prescriptions on oral
    anticoagulants (e.g. warfarin) and non-steroidal
    anti-inflammatory drugs (NSAIDs, e.g. ibuprofen).

    The frequency column reflects the maximum allowable
    doses per day. For the purposes of ARC HBR, where NSAIDs
    must be prescribed > 4 days/week, all prescriptions in
    the HIC data indicate frequency > 1 (i.e. at least one
    per day), and therefore qualify for ARC HBR purposes.

    Args:
        engine: The connection to the database

    Returns:
        The table of prescriptions, including the patient_id,
            order_date (to link to an episode), prescription name,
            prescription group (oac or nsaid), and frequency (in
            doses per day).
    """

    df = get_data(engine, hic.pharmacy_prescribing_query)

    prescriptions_of_interest = {
        "warfarin": "oac",
        "apixaban": "oac",
        "dabigatran etexilate": "oac",
        "edoxaban": "oac",
        "rivaroxaban": "oac",
        "ibuprofen": "nsaid",
        "naproxen": "nsaid",
        "diclofenac": "nsaid",
        "diclofenac sodium": "nsaid",
        "celecoxib": "nsaid",  # Not present in HIC data
        "mefenamic acid": "nsaid",  # Not present in HIC data
        "etoricoxib": "nsaid",
        "indometacin": "nsaid",  # This spelling is used in HIC data
        "indomethacin": "nsaid",  # Alternative spelling
        # "aspirin": "nsaid" -- not accounting for high dose
    }

    # Only keep prescriptions of interest
    df = df[df["name"].isin(prescriptions_of_interest.keys())]

    # Add the type of prescription to the table
    df["group"] = df["name"].map(prescriptions_of_interest)

    # Replace alternative spellings
    df["name"] = df["name"].str.replace("indomethacin", "indometacin")

    # Replace admission medicine column with bool
    on_admission_map = {"y": True, "n": False}
    df["on_admission"] = df["on_admission"].map(on_admission_map)

    # Extra spaces are not typos.
    per_day = {
        "TWICE a day": 2,
        "in the MORNING": 1,
        "THREE times a day": 3,
        "TWICE a day at 08:00 and 22:00": 2,
        "ONCE a day  at 18:00": 1,
        "up to every SIX hours": 4,
        "up to every EIGHT hours": 3,
        "TWICE a day at 08:00 and 20:00": 2,
        "up to every 24 hours": 1,
        "THREE times a day at 08:00 15:00 and 22:00": 3,
        "TWICE a day at 08:00 and 19:00": 2,
        "ONCE a day  at 20:00": 1,
        "ONCE a day  at 08:00": 1,
        "up to every 12 hours": 2,
        "ONCE a day  at 19:00": 1,
        "THREE times a day at 08:00 15:00 and 20:00": 3,
        "THREE times a day at 08:00 14:00 and 22:00": 3,
        "ONCE a day  at 22:00": 1,
        "every EIGHT hours": 24,
        "ONCE a day  at 09:00": 1,
        "up to every FOUR hours": 6,
        "TWICE a day at 06:00 and 18:00": 2,
        "at NIGHT": 1,
        "ONCE a day  at 14:00": 1,
        "ONCE a day  at 12:00": 1,
        "THREE times a day at 08:00 14:00 and 20:00": 3,
        "THREE times a day at 00:00 08:00 and 16:00": 3,
    }

    # Replace frequencies strings with doses per day
    df["frequency"] = df["frequency"].map(per_day)

    return df[
        ["patient_id", "order_date", "name", "group", "frequency", "on_admission"]
    ].reset_index(drop=True)


def link_to_episodes(
    items: pd.DataFrame, episodes: pd.DataFrame, date_col_name: str
) -> pd.DataFrame:
    """Link HIC laboratory test/prescriptions to episode by date

    Use this function to add an episode_id to the laboratory tests
    table or the prescriptions table. Tests/prescriptions are generically
    referred to as items below.

    This function associates each item with the first episode containing
    the item date in its [episode_start, episode_end) range. The column
    containing the item date is given by `date_col_name`.

    For prescriptions, use the prescription order date for linking. For
    laboratory tests, use the sample collected date.

    This function assumes that the episode_id in the episodes table is
    unique (i.e. no patients share an episode ID).

    For higher performance, reduce the item table to items of interest
    before calling this function.

    Since episodes may slightly overlap, an item may be associated
    with more than one episode. In this case, the function will associate
    the item with the earliest episode (the returned table will
    not contain duplicate items).

    Args:
        items: The prescriptions or laboratory tests table. Must contain a
            `date_col_name` column, which is used to compare with episode
            start/end dates, and the `patient_id`.

        episodes: The episodes table. Must contain `patient_id`, `episode_id`,
            `episode_start` and `episode_end`.

    Returns:
        The items table with the index `episode_id`.
    """

    # Before linking to episodes, add an item ID. This is to
    # remove duplicated items in the last step of linking,
    # due ot overlapping episode time windows.
    items["item_id"] = range(items.shape[0])

    # Join together all items and episode information by patient. Use
    # a left join on items (assuming items is narrowed to the item types
    # of interest) to keep the result smaller. Reset the index to move
    # episode_id to a column.
    with_episodes = pd.merge(items, episodes.reset_index(), how="left", on="patient_id")

    # Thinking of each row as both an episode and a item, drop any
    # rows where the item date does not fall within the start
    # and end of the episode (start date inclusive).
    consistent_dates = (
        with_episodes[date_col_name] >= with_episodes["episode_start"]
    ) & (with_episodes[date_col_name] < with_episodes["episode_end"])
    overlapping_episodes = with_episodes[consistent_dates]

    # Since some episodes overlap in time, some items will end up
    # being associated with more than one episode. Remove any
    # duplicates by associating only with the earliest episode.
    deduplicated = (
        overlapping_episodes.sort_values("episode_start").groupby("item_id").head(1)
    )

    # Keep episode_id, drop other episodes/unnecessary columns
    return (
        deduplicated.drop(columns=["item_id"])
        .drop(columns=[c for c in episodes.columns if c != "episode_id"])
        .set_index("episode_id", drop=True)
    )


def get_prescriptions(engine: Engine, episodes: pd.DataFrame) -> pd.DataFrame:
    """Get relevant prescriptions from the HIC data, linked to episode

    For information about the contents of the table, refer to the
    documentation for [get_unlinked_prescriptions()][pyhbr.middle.from_hic.get_unlinked_prescriptions].

    This function links each prescription to the first episode containing
    the prescription order date in its date range. For more about this, see
    [link_to_episodes()][pyhbr.middle.from_hic.link_to_episodes].

    Args:
        engine: The connection to the database
        episodes: The episodes table, used for linking. Must contain
            `patient_id`, `episode_id`, `episode_start` and `episode_end`.

    Returns:
        The table of prescriptions, including the prescription name,
            prescription group (oac or nsaid), frequency (in doses per day),
            and link to the associated episode.
    """
    prescriptions = get_unlinked_prescriptions(engine)
    return link_to_episodes(prescriptions, episodes, "order_date")


def get_lab_results(engine: Engine, episodes: pd.DataFrame) -> pd.DataFrame:
    """Get relevant laboratory results from the HIC data, linked to episode

    For information about the contents of the table, refer to the
    documentation for [get_unlinked_lab_results()][pyhbr.middle.from_hic.get_unlinked_lab_results].

    This function links each laboratory test to the first episode containing
    the sample collected date in its date range. For more about this, see
    [link_to_episodes()][pyhbr.middle.from_hic.link_to_episodes].

    Args:
        engine: The connection to the database
        episodes: The episodes table, used for linking. Must contain
            `patient_id`, `episode_id`, `episode_start` and `episode_end`.

    Returns:
        Table of laboratory results, including Hb (haemoglobin),
            platelet count, and eGFR (kidney function). The columns are
            `sample_date`, `test_name`, `episode_id`.
    """
    lab_results = get_unlinked_lab_results(engine)
    return link_to_episodes(lab_results, episodes, "sample_date")


def get_episodes(engine: Engine, start_date: date, end_date: date) -> pd.DataFrame:
    """Get the table of episodes

    Args:
        engine: The connection to the database
        start_date: The start date (inclusive) for returned episodes
        end_date:  The end date (inclusive) for returned episodes

    Returns:
        The episode date, indexed by episode_id
    """
    df = get_data(engine, hic.episodes_query, start_date, end_date)
    return df.set_index("episode_id", drop=True)


def get_demographics(engine: Engine) -> pd.DataFrame:
    """Get patient demographic information

    Gender is encoded using the NHS data dictionary values, which
    is mapped to a category column in the table. (Note that initial
    values are strings, not integers.)

    * "0": Not known. Mapped to "unknown"
    * "1": Male: Mapped to "male"
    * "2": Female. Mapped to "female"
    * "9": Not specified. Mapped to "unknown".

    Not mapping 0/9 to NA in case either is related to non-binary
    genders (i.e. it contains information, rather than being a NULL field).

    Args:
        engine: The connection to the database

    Returns:
        A table indexed by patient_id, containing gender, birth
            year, and death_date (if applicable).

    """
    df = get_data(engine, hic.demographics_query)
    df.set_index("patient_id", drop=True, inplace=True)

    # Convert gender to categories
    df["gender"] = df["gender"].replace("9", "0")
    df["gender"] = df["gender"].astype("category")
    df["gender"] = df["gender"].cat.rename_categories(
        {"0": "unknown", "1": "male", "2": "female"}
    )

    return df


class HicData:
    def __init__(self, engine: Engine, start_date: date, end_date: date):
        """Get the HIC dataset (collection of 5 tables)

        Args:
            engine: The connection to the database
            start_date: The start date (inclusive) for returned episodes
            end_date:  The end date (inclusive) for returned episodes

        Raises:
            RuntimeError: if the episode_id is not unique
        """

        self.codes = get_clinical_codes(
            engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml"
        )  # slow
        self.episodes = get_episodes(engine, start_date, end_date)  # fast
        self.prescriptions = get_prescriptions(engine, self.episodes)  # fast
        self.lab_results = get_lab_results(engine, self.episodes)  # really slow
        self.demographics = get_demographics(engine)

        if self.episodes.value_counts("episode_id").max() > 1:
            raise RuntimeError(
                "Found non-unique episode IDs; subsequent script will be invalid"
            )