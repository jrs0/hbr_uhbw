"""Data sources available from the BNSSG ICB

This file contains queries that fetch the raw data from the BNSSG
ICB, which includes hospital episode statistics (HES) and primary
care data.

This file does not include the HIC data transferred to the ICB.
"""

from itertools import product
from datetime import date
from sqlalchemy import select, Select, Engine, String, DateTime
from pyhbr.common import CheckedTable


def ordinal(n: int) -> str:
    """Make an an ordinal like "2nd" from a number n

    See https://stackoverflow.com/a/20007730.

    Args:
        n: The integer to convert to an ordinal string.

    Returns:
        For an integer (e.g. 5), the ordinal string (e.g. "5th")
    """
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return str(n) + suffix


def clinical_code_column_name(kind: str, position: int) -> str:
    """Make the primary/secondary diagnosis/procedure column names

    Args:
        kind: Either "diagnosis" or "procedure".
        position: 0 for primary, 1 and higher for secondaries.

    Returns:
        The column name for the clinical code compatible with
            the ICB HES tables.
    """

    if kind == "diagnosis":
        if position == 0:
            return "DiagnosisPrimary_ICD"

        return f"Diagnosis{ordinal(position)}Secondary_ICD"
    else:
        if position == 0:
            # reversed compared to diagnoses
            return "PrimaryProcedure_OPCS"

        # Secondaries are offset by one compared to diagnoses
        return f"Procedure{ordinal(position+1)}_OPCS"


def sus_query(engine: Engine, start_date: date, end_date: date) -> Select:
    """Get the episodes list in the HES data

    This table contains one episode per row. Diagnosis/procedure clinical
    codes are represented in wide format (one clinical code position per
    columns), and patient demographic information is also included.

    Args:
        engine: the connection to the database
        start_date: first valid consultant-episode start date
        end_date: last valid consultant-episode start date

    Returns:
        SQL query to retrieve episodes table
    """
    table = CheckedTable("vw_apc_sem_001", engine)

    # Standard columns containing IDs, dates, patient demographics, etc
    columns = [
        table.col("AIMTC_Pseudo_NHS").cast(String).label("patient_id"),
        table.col("AIMTC_Age").cast(String).label("age"),
        table.col("Sex").cast(String).label("gender"),
        table.col("PBRspellID").cast(String).label("spell_id"),
        table.col("StartDate_ConsultantEpisode").label("episode_start"),
        table.col("EndDate_ConsultantEpisode").label("episode_end"),
    ]

    # Diagnosis and procedure columns are renamed to (diagnosis|procedure)_n,
    # where n begins from 1 (for the primary code; secondaries are represented
    # using n > 1)
    clinical_code_column_names = {
        clinical_code_column_name(kind, n): f"{kind}_{n+1}"
        for kind, n in product(["diagnosis", "procedure"], range(24))
    }

    clinical_code_columns = [
        table.col(real_name).cast(String).label(new_name)
        for real_name, new_name in clinical_code_column_names.items()
    ]

    # Append the clinical code columns to the other data columns
    columns += clinical_code_columns

    # Valid rows must have one of the following commissioner codes
    valid_list = ["5M8", "11T", "5QJ", "11H", "5A3", "12A", "15C", "14F", "Q65"]

    return select(*columns).where(
        table.col("StartDate_ConsultantEpisode") >= start_date,
        table.col("EndDate_ConsultantEpisode") <= end_date,
        table.col("AIMTC_Pseudo_NHS").is_not(None),
        table.col("AIMTC_Pseudo_NHS") != 9000219621,  # Invalid-patient marker
        table.col("AIMTC_OrganisationCode_Codeofcommissioner").in_(valid_list),
    )


def primary_care_attributes_query(engine: Engine, patient_ids: list[str]) -> Select:
    """Get primary care patient information

    This is translated into an IN clause, which has an item limit. 
    If patient_ids is longer than 2000, an error is raised. If 
    more patient IDs are needed, split patient_ids and call this
    function multiple times.
    
    The values in patient_ids must be valid (they should come from
    a query such as sus_query).

    Args:
        engine: The connection to the database
        patient_ids: The list of patient identifiers to filter
            the nhs_number column.

    Returns:
        SQL query to retrieve episodes table
    """
    if len(patient_ids) > 2000:
        raise ValueError("The list patient_ids must be less than 2000 long.")
    
    table = CheckedTable("primary_care_attributes", engine)

    return select(
        table.col("nhs_number").cast(String).label("patient_id"),
        table.col("attribute_period").cast(DateTime),
        table.col("homeless"),
        
        # No need for these, available in episodes data
        #table.col("age"),
        #table.col("sex"),
        
        table.col("smoking"),
        table.col("bmi"),
        table.col("ethnicity"),
        table.col("veteran"),
        table.col("lsoa"),
        table.col("religion"),
        table.col("prim_language"),
        table.col("marital"),
        table.col("sexual_orient"),
        table.col("gender_identity"),
        table.col("pregnancy"),
        table.col("alcohol_cscore"),
        table.col("alcohol_units"),
        table.col("gppaq"),
        table.col("health_check"),
        table.col("mmr1"),
        table.col("mmr2"),
        table.col("qrisk2_3"),
        table.col("live_birth"),
        table.col("newborn_check"),
        table.col("infant_feeding"),
        table.col("newborn_weight"),
        table.col("diabetes_gest"),
        table.col("polypharmacy_repeat"),
        table.col("polypharmacy_acute"),
        table.col("hearing_impair"),
        table.col("visual_impair"),
        table.col("phys_disability"),
        table.col("efi_category"),
        table.col("eol_plan"),
        table.col("pref_death"),
        table.col("epaccs"),
        table.col("dna_cpr"),
        table.col("is_carer"),
        table.col("has_carer"),
        table.col("housebound"),
        table.col("nh_rh"),
        table.col("organ_transplant"),
        table.col("screen_eye"),
        table.col("screen_cervical"),
        table.col("screen_breast"),
        table.col("screen_bowel"),
        table.col("screen_aaa"),
        table.col("egfr"),
        table.col("fev1"),
        table.col("mrc_dyspnoea"),
        table.col("gout"),
        table.col("inflam_arthritic"),
        table.col("osteoarthritis"),
        table.col("anaemia_other"),
        table.col("anaemia_iron"),
        table.col("coag"),
        table.col("sickle"),
        table.col("osteoporosis"),
        table.col("ricketts"),
        table.col("cancer_lung"),
        table.col("cancer_breast"),
        table.col("cancer_bowel"),
        table.col("cancer_prostate"),
        table.col("cancer_leuklymph"),
        table.col("cancer_cervical"),
        table.col("cancer_ovarian"),
        table.col("cancer_melanoma"),
        table.col("cancer_nonmaligskin"),
        table.col("cancer_headneck"),
        table.col("cancer_giliver"),
        table.col("cancer_other"),
        table.col("cancer_metase"),
        table.col("cancer_bladder"),
        table.col("cancer_kidney"),
        table.col("cancer_lung_year"),
        table.col("cancer_breast_year"),
        table.col("cancer_bowel_year"),
        table.col("cancer_prostate_year"),
        table.col("cancer_leuklymph_year"),
        table.col("cancer_cervical_year"),
        table.col("cancer_ovarian_year"),
        table.col("cancer_melanoma_year"),
        table.col("cancer_nonmaligskin_year"),
        table.col("cancer_headneck_year"),
        table.col("cancer_giliver_year"),
        table.col("cancer_other_year"),
        table.col("cancer_metase_year"),
        table.col("cancer_bladder_year"),
        table.col("cancer_kidney_year"),
        table.col("ihd_nonmi"),
        table.col("af"),
        table.col("arrhythmia_other"),
        table.col("stroke"),
        table.col("ihd_mi"),
        table.col("hf"),
        table.col("ht"),
        table.col("bp_date"),
        table.col("bp_reading"),
        table.col("vasc_dis"),
        table.col("cardio_other"),
        table.col("eczema"),
        table.col("psoriasis"),
        table.col("pre_diabetes"),
        table.col("diabetes_1"),
        table.col("diabetes_2"),
        table.col("diabetes_retina"),
        table.col("thyroid"),
        table.col("endocrine_other"),
        table.col("coeliac"),
        table.col("stomach"),
        table.col("ibd"),
        table.col("ibs"),
        table.col("liver_alcohol"),
        table.col("liver_nafl"),
        table.col("hep_b"),
        table.col("hep_c"),
        table.col("liver_other"),
        table.col("endometriosis"),
        table.col("uterine"),
        table.col("pelvic"),
        table.col("poly_ovary"),
        table.col("abortion"),
        table.col("miscarriage"),
        table.col("contraception"),
        table.col("incont_urinary"),
        table.col("nose"),
        table.col("angio_anaph"),
        table.col("hiv"),
        table.col("obesity"),
        table.col("dep_alcohol"),
        table.col("dep_opioid"),
        table.col("dep_cocaine"),
        table.col("dep_cannabis"),
        table.col("dep_benzo"),
        table.col("dep_other"),
        table.col("adhd"),
        table.col("sad"),
        table.col("depression"),
        table.col("disorder_eating"),
        table.col("smi"),
        table.col("disorder_pers"),
        table.col("ptsd"),
        table.col("self_harm"),
        table.col("back_pain"),
        table.col("fragility"),
        table.col("neuro_various"),
        table.col("autism"),
        table.col("fatigue"),
        table.col("neuro_pain"),
        table.col("dementia"),
        table.col("learning_diff"),
        table.col("epilepsy"),
        table.col("learning_dis"),
        table.col("migraine"),
        table.col("mnd"),
        table.col("ms"),
        table.col("parkinsons"),
        table.col("macular_degen"),
        table.col("cataracts"),
        table.col("ckd"),
        table.col("asthma"),
        table.col("copd"),
        table.col("cystic_fibrosis"),
        table.col("lung_restrict"),
        table.col("tb"),
        table.col("amputations"),
        table.col("measles_mumps"),
        table.col("qof_af"),
        table.col("qof_chd"),
        table.col("qof_hf"),
        table.col("qof_ht"),
        table.col("qof_pad"),
        table.col("qof_stroke"),
        table.col("qof_asthma"),
        table.col("qof_copd"),
        table.col("qof_obesity"),
        table.col("qof_cancer"),
        table.col("qof_ckd"),
        table.col("qof_diabetes"),
        table.col("qof_pall"),
        table.col("qof_dementia"),
        table.col("qof_depression"),
        table.col("qof_epilepsy"),
        table.col("qof_learndis"),
        table.col("qof_mental"),
        table.col("qof_osteoporosis"),
        table.col("qof_rheumarth"),
    ).where(table.col("nhs_number").in_(patient_ids))


def primary_care_prescriptions_query(
    engine: Engine, patient_ids: list[str]
) -> Select:
    """Get medications dispensed in primary care

    Args:
        engine: the connection to the database
        patient_ids: The list of patient identifiers to filter
            the nhs_number column.

    Returns:
        SQL query to retrieve episodes table
    """
    table = CheckedTable("prescription", engine, schema="swd")

    return select(
        table.col("nhs_number").cast(String).label("patient_id"),
        table.col("prescription_date").label("date"),
        table.col("prescription_name").label("name"),
        table.col("prescription_quantity").label("quantity"),
        table.col("prescription_type").label("acute_or_repeat"),
    ).where(
        table.col("nhs_number").in_(patient_ids)
    )


def primary_care_measurements_query(
    engine: Engine, patient_ids: list[str]
) -> Select:
    """Get physiological measurements performed in primary care

    Args:
        engine: the connection to the database
        patient_ids: The list of patient identifiers to filter
            the nhs_number column.

    Returns:
        SQL query to retrieve episodes table
    """
    table = CheckedTable("measurement", engine, schema="swd")

    return select(
        table.col("nhs_number").cast(String).label("patient_id"),
        table.col("measurement_date").label("date"),
        table.col("measurement_name").label("name"),
        table.col("measurement_value").label("result"),
        table.col("measurement_group").label("group"),
    ).where(
        table.col("nhs_number").in_(patient_ids)
    )
