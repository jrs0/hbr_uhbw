"""SQL queries and functions for HIC (UHBW) data.
"""

def demographics_query():
    """Get demographic information from HIC data

    The date/time at which the data was obtained is
    not stored in the table, but patient age can be
    computed from the date of the episode under consideration
    and the year_of_birth in this table.

    The underlying table does have a cause_of_death column,
    but it is all null, so not included.

    Returns:
        (str): SQL query to retrieve episodes table
    """
    return (
        "select subject as patient_id"
        ",gender"
        ",year_of_birth"
        ",death_date"
        " from hic_cv_test.dbo.cv1_demographics"
    )

def episodes_query(start_date, end_date):
    """Get the episodes list in the HIC data

    This table does not contain any episode information,
    just a patient and an episode id for linking to diagnosis
    and procedure information in other tables.

    Args:
        start_date (datetime.date): first valid consultant-episode start date
        end_date (datetime.date): last valid consultant-episode start date

    Returns:
        (str): SQL query to retrieve episodes table
    """
    return (
        "select subject as patient_id"
        ",spell_identifier as spell_id"
        ",episode_identifier as episode_id"
        ",episode_start_time as episode_start"
        ",episode_end_time as episode_end"
        " from hic_cv_test.dbo.cv1_episodes"
        f" where episode_start_time between '{start_date}' and '{end_date}'"
    )

def diagnoses_query():
    """Get the diagnoses corresponding to episodes

    This should be linked to the episodes table to
    obtain information about the diagnoses in the episode.

    Diagnoses are encoded using ICD-10 codes, and the
    position column contains the order of diagnoses in
    the episode (1-indexed).

    Returns:
        (str): SQL query to retrieve diagnoses table
    """
    return (
        "select episode_identifier as episode_id"
        ",diagnosis_date_time as time"
        ",diagnosis_position as position"
        ",diagnosis_code_icd as icd"
        " from hic_cv_test.dbo.cv1_episodes_diagnosis"
    )

def procedures_query():
    """Get the procedures corresponding to episodes

    This should be linked to the episodes table to
    obtain information about the procedures in the episode.

    Procedures are encoded using OPCS-4 codes, and the
    position column contains the order of procedures in
    the episode (1-indexed).
    
    Returns:
        (str): SQL query to retrieve procedures table
    """
    return (
        "select episode_identifier as episode_id"
        ",procedure_date_time as time"
        ",procedure_position as position"
        ",procedure_code_opcs as opcs"
        " from hic_cv_test.dbo.cv1_episodes_procedures"
    )

def pathology_blood_query(investigations = ["OBR_BLS_UE", "OBR_BLE_FB"]):
    """Get the table of blood test results in the HIC data

    Since blood tests in this table are not associated with an episode
    directly by key, it is necessary to link them based on the patient
    identifier and date. This operation can be quite slow if the blood
    tests table is large. One way to reduce the size is to filter by
    investigation using the investigations parameter. The investigation
    codes in the HIC data are shown below:

    | `investigation` | Description |
    |--------------------|-------------|
    | OBR_BLS_UL |                          LFT|
    | OBR_BLS_UE |    UREA,CREAT + ELECTROLYTES|
    | OBR_BLS_FB |             FULL BLOOD COUNT|
    | OBR_BLS_UT |        THYROID FUNCTION TEST|
    | OBR_BLS_TP |                TOTAL PROTEIN|
    | OBR_BLS_CR |           C-REACTIVE PROTEIN|
    | OBR_BLS_CS |              CLOTTING SCREEN|
    | OBR_BLS_FI |                        FIB-4|
    | OBR_BLS_AS |                          AST|
    | OBR_BLS_CA |                CALCIUM GROUP|
    | OBR_BLS_TS |                  TSH AND FT4|
    | OBR_BLS_FO |                SERUM FOLATE|
    | OBR_BLS_PO |                    PHOSPHATE|
    | OBR_BLS_LI |                LIPID PROFILE|
    | OBR_POC_VG | POCT BLOOD GAS VENOUS SAMPLE|
    | OBR_BLS_HD |              HDL CHOLESTEROL|
    | OBR_BLS_FT |                      FREE T4|
    | OBR_BLS_FE |               SERUM FERRITIN|
    | OBR_BLS_GP |    ELECTROLYTES NO POTASSIUM|
    | OBR_BLS_CH |                  CHOLESTEROL|
    | OBR_BLS_MG |                    MAGNESIUM|
    | OBR_BLS_CO |                     CORTISOL|

    Each test is similarly encoded. The valid test codes in the full
    blood count and U+E investigations are shown below:

    | `investigation` | `test` | Description |
    |-----------------|--------|-------------|
    | OBR_BLS_FB | OBX_BLS_NE |           Neutrophils|
    | OBR_BLS_FB | OBX_BLS_PL |             Platelets|
    | OBR_BLS_FB | OBX_BLS_WB |      White Cell Count|
    | OBR_BLS_FB | OBX_BLS_LY |           Lymphocytes|
    | OBR_BLS_FB | OBX_BLS_MC |                   MCV|
    | OBR_BLS_FB | OBX_BLS_HB |           Haemoglobin|
    | OBR_BLS_FB | OBX_BLS_HC |           Haematocrit|
    | OBR_BLS_UE | OBX_BLS_NA |                Sodium|
    | OBR_BLS_UE | OBX_BLS_UR |                  Urea|
    | OBR_BLS_UE | OBX_BLS_K  |             Potassium|
    | OBR_BLS_UE | OBX_BLS_CR |            Creatinine|
    | OBR_BLS_UE | OBX_BLS_EP | eGFR/1.73m2 (CKD-EPI)|
    
    Args:
        investigation_codes (list[str]): Which types of laboratory
            test to include in the query. Fetching fewer types of
            test makes the query faster.

    Returns:
        (str): SQL query to retrieve blood tests table
    """
    return (
        "select subject as patient_id"
        ",investigation_code as investigation"
        ",test_code as test"
        ",test_result as result"
        ",test_result_unit as unit"
        ",sample_collected_date_time as sample_date"
        ",result_available_date_time as result_date"
        ",result_flag"
        ",result_lower_range"
        ",result_upper_range"
        " from hic_cv_test.dbo.cv1_pathology_blood"
        f" where investigation_code in {investigations}"
    )