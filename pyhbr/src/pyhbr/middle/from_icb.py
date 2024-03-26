from pandas import DataFrame, concat
from pyhbr import clinical_codes


def get_episodes(raw_sus_data: DataFrame) -> DataFrame:
    """Get the episodes table

    Args:
        raw_sus_data: Data returned by sus_query() query.

    Returns:
        A dataframe indexed by `episode_id`, with columns
            `episode_start`, `spell_id` and `patient_id`.
    """
    return (
        raw_sus_data[["spell_id", "patient_id", "episode_start"]]
        .reset_index(names="episode_id")
        .set_index("episode_id")
    )


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