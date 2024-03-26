from pandas import DataFrame, concat
from pyhbr import clinical_codes, common
from pyhbr.data_source import icb
from sqlalchemy import Engine
from datetime import date


def get_episodes(raw_sus_data: DataFrame) -> DataFrame:
    """Get the episodes table

    Args:
        raw_sus_data: Data returned by sus_query() query.

    Returns:
        A dataframe indexed by `episode_id`, with columns
            `episode_start`, `spell_id` and `patient_id`.
    """
    return (
        raw_sus_data[["spell_id", "patient_id", "episode_start", "age"]]
        .reset_index(names="episode_id")
        .set_index("episode_id")
    )


def get_demographics(raw_sus_data: DataFrame) -> DataFrame:
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
    df = raw_sus_data[["gender", "patient_id"]].copy()
    df.set_index("patient_id", drop=True, inplace=True)

    # Convert gender to categories
    df["gender"] = df["gender"].replace("9", "0")
    df["gender"] = df["gender"].astype("category")
    df["gender"] = df["gender"].cat.rename_categories(
        {"0": "unknown", "1": "male", "2": "female"}
    )

    return df


def get_long_clincial_codes(raw_sus_data: DataFrame) -> DataFrame:
    """Get a table of the clinical codes in long format

    This is modelled on the format of the HIC data, which works
    well, and makes it possible to re-use the code for processing
    that table

    Args:
        raw_sus_data: Must contain one row per episode, and
            contains clinical codes in wide format, with
            columns `diagnosis_n` and `procedure_n`, for
            n > 0. The value n == 1 is the primary diagnosis
            or procedure, and n > 1 is for secondary codes.

    Returns:
        A table containing
    """

    # Pivot the wide format to long based on the episode_id
    df = (
        raw_sus_data.reset_index(names="episode_id")
        .filter(regex="(diagnosis|procedure|episode_id)")
        .melt(id_vars="episode_id", value_name="code")
    )

    # Drop any codes that are empty or whitespace
    long_codes = df[~df["code"].str.isspace() & (df["code"] != "")].copy()

    # Convert the diagnosis/procedure and value of n into separate columns
    long_codes[["type", "position"]] = long_codes["variable"].str.split(
        "_", expand=True
    )

    long_codes["position"] = long_codes["position"].astype(int)

    # Collect columns of interest and sort for ease of viewing
    return (
        long_codes[["episode_id", "code", "type", "position"]]
        .sort_values(["episode_id", "type", "position"])
        .reset_index(drop=True)
    )


def get_clinical_codes(
    raw_sus_data: DataFrame, diagnoses_file: str, procedures_file: str
) -> DataFrame:
    """Get clinical codes in long format and normalised form.

    Args:
        raw_sus_data: Must contain one row per episode, and
            contains clinical codes in wide format, with
            columns `diagnosis_n` and `procedure_n`, for
            n > 0. The value n == 1 is the primary diagnosis
            or procedure, and n > 1 is for secondary codes.
        diagnoses_file: The diagnoses codes file name (loaded from the package)
        procedures_file: The procedures codes file name (loaded from the package)

    Returns:
        A table containing diagnoses/procedures, normalised codes, code groups,
            diagnosis positions, and associated episode ID.
    """

    long_codes = get_long_clincial_codes(raw_sus_data)

    diagnosis_codes = clinical_codes.load_from_package(diagnoses_file)
    procedures_codes = clinical_codes.load_from_package(procedures_file)

    # Fetch the data from the server
    diagnoses = long_codes[long_codes["type"] == "diagnosis"].copy()
    procedures = long_codes[long_codes["type"] == "procedure"].copy()

    # Reduce data to only code groups, and combine diagnoses/procedures
    filtered_diagnoses = clinical_codes.filter_to_groups(diagnoses, diagnosis_codes)
    filtered_procedures = clinical_codes.filter_to_groups(procedures, procedures_codes)

    # Tag the diagnoses/procedures, and combine the tables
    filtered_diagnoses["type"] = "diagnosis"
    filtered_procedures["type"] = "procedure"

    codes = concat([filtered_diagnoses, filtered_procedures])
    codes["type"] = codes["type"].astype("category")

    return codes


def get_episodes_and_demographics(
    engine: Engine, start_date: date, end_date: date
) -> dict[str, DataFrame]:
    """Get episode and clinical code data

    This batch of data must be fetched first to find index events,
    which establishes the patient group of interest. This can then
    be used to narrow subsequent queries to the data base, to speed
    them up.

    Args:
        engine: The connection to the database
        start_date: The start date (inclusive) for returned episodes
        end_date:  The end date (inclusive) for returned episodes

    Returns:
        A dictionary containing "episode"," codes" and "demographics" tables.
    """
    
    # The fetch is very slow (and varies depending on the internet connection).
    # Fetching 5 years of data takes approximately 20 minutes (about 2m episodes).
    print("Starting SUS data fetch...")
    raw_sus_data = common.get_data(engine, icb.sus_query, start_date, end_date)
    print("SUS data fetch finished.")

    # Compared to the data fetch, this part is relatively fast, but still very
    # slow (approximately 10% of the total runtime).
    episodes = get_episodes(raw_sus_data)
    codes = get_clinical_codes(raw_sus_data, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml")
    demographics = get_demographics(raw_sus_data)

    return {"episodes": episodes, "codes": codes, "demographics": demographics}
