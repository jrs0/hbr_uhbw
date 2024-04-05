import numpy as np
import pandas as pd
from pandas import DataFrame, Series, concat
from pyhbr import clinical_codes, common
from pyhbr.data_source import icb
from sqlalchemy import Engine
from datetime import date
import datetime as dt
from pyhbr.clinical_codes import counting


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


def process_flag_columns(primary_care_attributes: DataFrame) -> DataFrame:
    """Replace NaN with false and convert to bool for a selection of rows

    Many columns in the primary care attributes encode a flag
    using 1 for true and NA/NULL for false. These must be replaced
    with a boolean type so that NA can distinguish missing data. 
    Instead of using a `bool`, use Int8 so that NaNs can be stored.
    (This is important later on for index spells with missing attributes,
    which need to store NaN in these flag columns.)

    Args:
        primary_care_attributes: Original table containing
            1/NA flag columns

    Returns:
        The primary care attributes with flag columns encoded
            as Int8.

    """
    
    # Columns interpreted as flags have been taken from
    # the SWD guide, where the data format column says
    # 1/Null. SWD documentation has been taken as a proxy
    # for the primary care attributes table (which does
    # not have column documentation).
    flag_columns = [
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
        # Not sure what *_year means as a flag
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
    df[flag_columns] = (
        df[flag_columns].astype("float").fillna(0).astype("Int8")
    )
    return df

def preprocess_smoking(column: Series) -> Series:
    """Convert the smoking column from string to category

    The values in the column are "unknown", "ex", "Unknown",
    "current", "Smoker", "Ex", and "Never".

    Based on the distribution of values in the column, it
    likely that "Unknown/unknown" mostly means "no". This
    makes the percentage of smoking about 15%, which is
    roughly in line with the average. Without performing this
    mapping, smokers outnumber non-smokers ("Never") approx.
    20 to 1.

    Note that the column does also include NA values, which
    will be left as NA.

    Args:
        column: The smoking column from the primary
            care attributes

    Returns:
        A category column containing "yes", "no", and "ex".
    """

    value_map = {
        "unknown": "no",
        "Unknown": "no",
        "current": "yes",
        "Smoker": "yes",
        "ex": "ex",
        "Ex": "ex",
        "Never": "no",
    }

    return column.map(value_map).astype("category")


def preprocess_ethnicity(column: Series) -> Series:
    """Map the ethnicity column to standard ethnicities.

    Ethnicities were obtained from www.ethnicity-facts-figures.service.gov.uk/style-guide/ethnic-groups,
    from the 2021 census:

    * asian_or_asian_british
    * black_black_british_caribbean_or_african
    * mixed_or_multiple_ethnic_groups
    * white
    * other_ethnic_group

    Args:
        column: A column of object ("string") containing
            ethnicities from the primary care attributes table.

    Returns:
        A column of type category containing the standard
            ethnicities (and NaN).
    """

    column = column.str.replace(" - ethnic category 2001 census", "")
    column = column.str.replace(" - England and Wales ethnic category 2011 census", "")
    column = column.str.replace(" - 2011 census England and Wales", "")
    column = column.str.replace(" - Scotland ethnic category 2011 census", "")
    column = column.str.replace(" - 2001 census", "")
    column = column.str.lower()
    column = column.str.replace("(\(|\)|:| )+", "_", regex=True)

    ethnicity_map = {
        "white_british": "white",
        "british_or_mixed_british": "white",
        "white_english_or_welsh_or_scottish_or_northern_irish_or_british": "white",
        "english": "white",
        "other_white_background": "white",
        "white": "white",
        "ethnic_category_not_stated": np.nan,
        "pakistani_or_british_pakistani": "asian_or_asian_british",
        "refusal_by_patient_to_provide_information_about_ethnic_group": np.nan,
        "ethnic_category": np.nan,
        "indian_or_british_indian": "asian_or_asian_british",
        "caribbean": "black_black_british_caribbean_or_african",
        "other_asian_background": "asian_or_asian_british",
        "african": "black_black_british_caribbean_or_african",
        "white_any_other_white_background": "white",
        "bangladeshi_or_british_bangladeshi": "asian_or_asian_british",
        "irish": "white",
        "white_irish": "white",
        "white_-_ethnic_group": "white",
        "chinese": "asian_or_asian_british",
        "polish": "white",
        "black_british": "black_black_british_caribbean_or_african",
        "white_and_black_caribbean": "mixed_or_multiple_ethnic_groups",
        "pakistani": "asian_or_asian_british",
        "other": "other_ethnic_group",
        "black_african": "black_black_british_caribbean_or_african",
        "asian_or_asian_british_indian": "asian_or_asian_british",
        "black_caribbean": "black_black_british_caribbean_or_african",
        "indian": "asian_or_asian_british",
        "asian_or_asian_british_pakistani": "asian_or_asian_british",
        "other_white_european_or_european_unspecified_or_mixed_european": "white",
        "somali": "black_black_british_caribbean_or_african",
        "ethnic_group_not_recorded": np.nan,
        "asian_or_asian_british_any_other_asian_background": "asian_or_asian_british",
        "white_and_asian": "mixed_or_multiple_ethnic_groups",
        "white_and_black_african": "mixed_or_multiple_ethnic_groups",
        "other_black_background": "black_black_british_caribbean_or_african",
        "italian": "white",
        "scottish": "white",
        "other_white_or_white_unspecified": "white",
        "other_ethnic_group_any_other_ethnic_group": "other_ethnic_group",
        "other_mixed_background": "mixed_or_multiple_ethnic_groups",
        "other_european_nmo_": "white",
        "welsh": "white",
        "greek": "white",
        "patient_ethnicity_unknown": np.nan,
        "mixed_multiple_ethnic_groups_any_other_mixed_or_multiple_ethnic_background": "mixed_or_multiple_ethnic_groups",
        "black_or_african_or_caribbean_or_black_british_caribbean": "black_black_british_caribbean_or_african",
        "filipino": "asian_or_asian_british",
        "ethnic_group": np.nan,
        "other_mixed_white": "white",  # Unclear
        "british_asian": "asian_or_asian_british",
        "iranian": "other_ethnic_group",
        "other_asian_ethnic_group": "asian_or_asian_british",
        "kurdish": "other_ethnic_group",
        "black_or_african_or_caribbean_or_black_british_african": "black_black_british_caribbean_or_african",
        "other_asian_nmo_": "asian_or_asian_british",
        "moroccan": "other_ethnic_group",
        "other_white_british_ethnic_group": "white",
        "mixed_multiple_ethnic_groups_white_and_black_caribbean": "mixed_or_multiple_ethnic_groups",
        "black_and_white": "mixed_or_multiple_ethnic_groups",
        "asian_or_asian_british_bangladeshi": "asian_or_asian_british",
        "mixed_multiple_ethnic_groups_white_and_black_african": "mixed_or_multiple_ethnic_groups",
        "white_polish": "white",
        "asian_and_chinese": "asian_or_asian_british",
        "black_or_african_or_caribbean_or_black_british_other_black_or_african_or_caribbean_background": "black_black_british_caribbean_or_african",
        "black_and_asian": "black_black_british_caribbean_or_african",
        "white_scottish": "white",
        "any_other_group": "other_ethnic_group",
        "other_ethnic_non-mixed_nmo_": "other_ethnic_group",
        "ethnicity_and_other_related_nationality_data": np.nan,
        "caucasian_race": "white",
        "multi-ethnic_islands_mauritian_or_seychellois_or_maldivian_or_st_helena": "other_ethnic_group",
        "punjabi": "asian_or_asian_british",
        "albanian": "white",
        "turkish/turkish_cypriot_nmo_": "other_ethnic_group",
        "black_-_other_african_country": "black_black_british_caribbean_or_african",
        "other_black_or_black_unspecified": "black_black_british_caribbean_or_african",
        "sri_lankan": "asian_or_asian_british",
        "mixed_asian": "asian_or_asian_british",
        "other_black_ethnic_group": "black_black_british_caribbean_or_african",
        "bulgarian": "white",
        "sikh": "asian_or_asian_british",
        "other_ethnic_mixed_origin": "other_ethnic_group",
        "n_african_arab/iranian_nmo_": "other_ethnic_group",
        "south_and_central_american": "other_ethnic_group",
        "asian_or_asian_british_chinese": "asian_or_asian_british",
        "ethnic_groups_census_nos": np.nan,
        "arab": "other_ethnic_group",
        "ethnic_group_finding": np.nan,
        "white_any_other_white_ethnic_group": "white",
        "greek_cypriot": "white",
        "latin_american": "other_ethnic_group",
        "other_asian_or_asian_unspecified": "asian_or_asian_british",
        "cypriot_part_not_stated_": "other_ethnic_group",
        "east_african_asian": "other_ethnic_group",
        "mixed_multiple_ethnic_groups_white_and_asian": "mixed_or_multiple_ethnic_groups",
        "other_ethnic_group_arab_arab_scottish_or_arab_british": "other_ethnic_group",
        "other_ethnic_group_arab": "other_ethnic_group",
        "turkish": "other_ethnic_group",
        "north_african": "black_black_british_caribbean_or_african",
        "greek_nmo_": "white",
        "bangladeshi": "asian_or_asian_british",
        "chinese_and_white": "mixed_or_multiple_ethnic_groups",
        "white_gypsy_or_irish_traveller": "white",
        "vietnamese": "asian_or_asian_british",
        "romanian": "white",
        "serbian": "white",
    }

    return column.map(ethnicity_map).astype("category")


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

    hba1c = df[df.name.str.contains("hba1c")][["patient_id", "date", "result"]].copy()
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

    most_recent_hba1c = (
        hba1c_before_index.sort_values("date").groupby("spell_id").tail(1)
    )
    prior_hba1c = swd_index_spells.merge(
        most_recent_hba1c, how="left", on="spell_id"
    ).set_index("spell_id")[["hba1c"]]

    return prior_hba1c
