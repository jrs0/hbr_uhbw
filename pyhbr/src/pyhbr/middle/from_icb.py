from pandas import DataFrame, concat
from pyhbr import clinical_codes, common
from pyhbr.data_source import icb
from sqlalchemy import Engine
from datetime import date


def get_episodes(raw_sus_data: DataFrame) -> DataFrame:
    """Get the episodes table

    Age and gender are also included in each row.

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
        raw_sus_data: Data returned by sus_query() query.

    Returns:
        A dataframe indexed by `episode_id`, with columns
            `episode_start`, `spell_id` and `patient_id`.
    """
    df = (
        raw_sus_data[["spell_id", "patient_id", "episode_start", "age", "gender"]]
        .reset_index(names="episode_id")
        .set_index("episode_id")
    )

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


def get_raw_sus_data(engine: Engine, start_date: date, end_date: date) -> DataFrame:
    """Get the raw SUS (secondary uses services hospital episode statistics)


    Args:
        engine: The connection to the database
        start_date: The start date (inclusive) for returned episodes
        end_date:  The end date (inclusive) for returned episodes

    Returns:
        A dataframe with one row per episode, containing clinical code
            data and patient demographics at that episode.
    """

    # The fetch is very slow (and varies depending on the internet connection).
    # Fetching 5 years of data takes approximately 20 minutes (about 2m episodes).
    print("Starting SUS data fetch...")
    raw_sus_data = common.get_data(engine, icb.sus_query, start_date, end_date)
    print("SUS data fetch finished.")

    return raw_sus_data


def get_episodes_and_codes(raw_sus_data: DataFrame) -> dict[str, DataFrame]:
    """Get episode and clinical code data

    This batch of data must be fetched first to find index events,
    which establishes the patient group of interest. This can then
    be used to narrow subsequent queries to the data base, to speed
    them up.

    Args:
        raw_sus_data: The raw HES data returned by get_raw_sus_data()

    Returns:
        A dictionary with "episodes" containing the episodes table
            (also contains age and gender) and "codes" containing the
            clinical code data in long format.
    """

    # Compared to the data fetch, this part is relatively fast, but still very
    # slow (approximately 10% of the total runtime).
    episodes = get_episodes(raw_sus_data)
    codes = get_clinical_codes(raw_sus_data, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml")

    return {"episodes": episodes, "codes": codes}


def replace_nan_with_zero(primary_care_attributes: DataFrame) -> DataFrame:
    """Replace NaN with zero for a selection of rows

    Many column in the primary care attributes data use NA
    as a marker for 0. It is important to replace these NAs
    with zero before performing a join of the attributes onto
    a larger table, which could produce NAs that mean "row
    was not present in attributes").

    Args:
        primary_care_attributes: Table where a subset of columns
            should have NaN replaced with zero.
            
    Returns:
        The modified attributes
    
    """
    na_means_zero = [
        "abortion",
        "adhd",
        "af",
        "amputations",
        "anaemia_iron",
        "anaemia_other",
        "angio_anaph",
        "arrhythmia_other",
        "asthma",
        "autism",
        "back_pain",
        "cancer_bladder",
        "cancer_bladder_year",
        "cancer_bowel",
        "cancer_bowel_year",
        "cancer_breast",
        "cancer_breast_year",
        "cancer_cervical",
        "cancer_cervical_year",
        "cancer_giliver",
        "cancer_giliver_year",
        "cancer_headneck",
        "cancer_headneck_year",
        "cancer_kidney",
        "cancer_kidney_year",
        "cancer_leuklymph",
        "cancer_leuklymph_year",
        "cancer_lung",
        "cancer_lung_year",
        "cancer_melanoma",
        "cancer_melanoma_year",
        "cancer_metase",
        "cancer_metase_year",
        "cancer_other",
        "cancer_other_year",
        "cancer_ovarian",
        "cancer_ovarian_year",
        "cancer_prostate",
        "cancer_prostate_year",
        "cardio_other",
        "cataracts",
        "ckd",
        "coag",
        "coeliac",
        "contraception",
        "copd",
        "cystic_fibrosis",
        "dementia",
        "dep_alcohol",
        "dep_benzo",
        "dep_cannabis",
        "dep_cocaine",
        "dep_opioid",
        "dep_other",
        "depression",
        "diabetes_1",
        "diabetes_2",
        "diabetes_gest",
        "diabetes_retina",
        "disorder_eating",
        "disorder_pers",
        "dna_cpr",
        "eczema",
        "endocrine_other",
        "endometriosis",
        "eol_plan",
        "epaccs",
        "epilepsy",
        "fatigue",
        "fragility",
        "gout",
        "has_carer",
        "health_check",
        "hearing_impair",
        "hep_b",
        "hep_c",
        "hf",
        "hiv",
        "homeless",
        "housebound",
        "ht",
        "ibd",
        "ibs",
        "ihd_mi",
        "ihd_nonmi",
        "incont_urinary",
        "inflam_arthritic",
        "is_carer",
        "learning_diff",
        "learning_dis",
        "live_birth",
        "liver_alcohol",
        "liver_nafl",
        "liver_other",
        "lung_restrict",
        "macular_degen",
        "measles_mumps",
        "migraine",
        "miscarriage",
        "mmr1",
        "mmr2",
        "mnd",
        "ms",
        "neuro_pain",
        "neuro_various",
        "newborn_check",
        "nh_rh",
        "nose",
        "obesity",
        "organ_transplant",
        "osteoarthritis",
        "osteoporosis",
        "parkinsons",
        "pelvic",
        "phys_disability",
        "poly_ovary",
        "pre_diabetes",
        "pregnancy",
        "psoriasis",
        "ptsd",
        "qof_af",
        "qof_asthma",
        "qof_chd",
        "qof_ckd",
        "qof_copd",
        "qof_dementia",
        "qof_depression",
        "qof_diabetes",
        "qof_epilepsy",
        "qof_hf",
        "qof_ht",
        "qof_learndis",
        "qof_mental",
        "qof_obesity",
        "qof_osteoporosis",
        "qof_pad",
        "qof_pall",
        "qof_rheumarth",
        "qof_stroke",
        "sad",
        "screen_aaa",
        "screen_bowel",
        "screen_breast",
        "screen_cervical",
        "screen_eye",
        "self_harm",
        "sickle",
        "smi",
        "stomach",
        "stroke",
        "tb",
        "thyroid",
        "uterine",
        "vasc_dis",
        "veteran",
        "visual_impair",
    ]
    
    df = primary_care_attributes.copy()
    df[na_means_zero] = df[na_means_zero].fillna(value=0).infer_objects(copy=False)
    return df


def get_primary_care_data(
    engine: Engine, patient_ids: list[str]
) -> dict[str, DataFrame]:
    """Fetch primary care information from the database

    Args:
        engine: The database connection
        patient_ids: A list of patient IDs to restrict the query.

    Returns:
        A map from table name to table containing
            "primary_care_attributes", "primary_care_prescriptions",
            and "primary_care_measurements".
    """

    # Primary care prescriptions
    primary_care_prescriptions = common.get_data_by_patient(
        engine, icb.primary_care_prescriptions_query, patient_ids
    )

    # Primary care measurements
    primary_care_measurements = common.get_data_by_patient(
        engine, icb.primary_care_measurements_query, patient_ids
    )

    # Primary care attributes
    df = common.get_data_by_patient(
        engine, icb.primary_care_attributes_query, patient_ids
    )
    primary_care_attributes = replace_nan_with_zero(df)

    return {
        "primary_care_attributes": primary_care_attributes,
        "primary_care_prescriptions": primary_care_prescriptions,
        "primary_care_measurements": primary_care_measurements,
    }
