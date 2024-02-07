"""SQL queries and functions for HIC (UHBW) data.
"""

from sqlalchemy import select
from sqlalchemy.exc import NoSuchTableError
from pyhbr.common import get_table

def demographics_query(engine):
    """Get demographic information from HIC data

    The date/time at which the data was obtained is
    not stored in the table, but patient age can be
    computed from the date of the episode under consideration
    and the year_of_birth in this table.

    The underlying table does have a cause_of_death column,
    but it is all null, so not included.

    Args:
        engine (sqlalchemy.Engine): the connection to the database
    
    Returns:
        (sqlalchemy.Select): SQL query to retrieve episodes table
    """
    table = get_table("cv1_demographics", engine)
    stmt = select(
        table.c.subject.label("patient_id"),
        table.c.gender,
        table.c.year_of_birth,
        table.c.death_date
    )
    return stmt


def episodes_query(engine, start_date, end_date):
    """Get the episodes list in the HIC data

    This table does not contain any episode information,
    just a patient and an episode id for linking to diagnosis
    and procedure information in other tables.

    Args:
        engine (sqlalchemy.Engine): the connection to the database
        start_date (datetime.date): first valid consultant-episode start date
        end_date (datetime.date): last valid consultant-episode start date

    Returns:
        (sqlalchemy.Select): SQL query to retrieve episodes table
    """
    table_name = "cv1_episodes"
    table = get_table(table_name, engine)
    try:
        stmt = select(
            table.c.subject.label("patient_id"),
            table.c.episode_identifier.label("episode_id"),
            table.c.spell_identifier.label("spell_id"),
            table.c.episode_start_time.label("episode_start"),
            table.c.episode_end_time.label("episode_end"),
        ).where(
            table.c.episode_start_time >= start_date,
            table.c.episode_end_timae <= end_date
        )
        return stmt
    except AttributeError as e:
        raise RuntimeError(f"Could not column name '{e}' in table '{table_name}'")

def diagnoses_query(engine):
    """Get the diagnoses corresponding to episodes

    This should be linked to the episodes table to
    obtain information about the diagnoses in the episode.

    Diagnoses are encoded using ICD-10 codes, and the
    position column contains the order of diagnoses in
    the episode (1-indexed).

    Args:
        engine (sqlalchemy.Engine): the connection to the database    
    
    Returns:
        (sqlalchemy.Select): SQL query to retrieve diagnoses table
    """
    table_name = "cv1_episodes_diagnosis"
    table = get_table(table_name, engine)
    try:
        stmt = select(
            table.c.episode_identifier.label("episode_id"),
            table.c.diagnosis_date_time.label("time"),
            table.c.diagnosis_position.label("position"),
            table.c.diagnosis_code_icd.label("icd"),
        )
        return stmt
    except AttributeError as e:
        raise RuntimeError(f"Could not column name '{e}' in table '{table_name}'")

def procedures_query(engine):
    """Get the procedures corresponding to episodes

    This should be linked to the episodes table to
    obtain information about the procedures in the episode.

    Procedures are encoded using OPCS-4 codes, and the
    position column contains the order of procedures in
    the episode (1-indexed).
    
    Args:
        engine (sqlalchemy.Engine): the connection to the database

    Returns:
        (sqlalchemy.Select): SQL query to retrieve procedures table
    """
    table_name = "cv1_episodes_procedures"
    table = get_table(table_name, engine)
    try:
        stmt = select(
            table.c.episode_identifier.label("episode_id"),
            table.c.procedure_date_time.label("time"),
            table.c.procedure_position.label("position"),
            table.c.procedure_code_opcs.label("opcs"),
        )
        return stmt
    except AttributeError as e:
        raise RuntimeError(f"Could not column name '{e}' in table '{table_name}'")

def pathology_blood_query(engine, investigations = ["OBR_BLS_UE", "OBR_BLE_FB"]):
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
        engine (sqlalchemy.Engine): the connection to the database
        investigation_codes (list[str]): Which types of laboratory
            test to include in the query. Fetching fewer types of
            test makes the query faster.

    Returns:
        (sqlalchemy.Select): SQL query to retrieve blood tests table
    """
    table_name = "cv1_pathology_blood"
    try:
        table = get_table(table_name, engine)
    except NoSuchTableError as e:
        raise RuntimeError(f"Could not find table '{e}' in database connection '{engine.url}'")
    try:
        stmt = select(
            table.c.subject.label("patient_id"),
            table.c.investigation_code.label("investigation"),
            table.c.test_code.label("test"),
            table.c.test_result.label("result"),
            table.c.test_result_unit.label("unit"),
            table.c.sample_collected_date_time.label("sample_date"),
            table.c.result_available_date_time.label("result_date"),
            table.c.result_flag,
            table.c.result_lower_range,
            table.c.result_upper_range
        ).where(table.c.investigation_code.in_(investigations))
        return stmt
    except AttributeError as e:
        raise RuntimeError(f"Could not column name '{e}' in table '{table_name}'")
