"""SQL queries and functions for HIC (UHBW) data.
"""

from datetime import date
from sqlalchemy import select, Select, Engine
from pyhbr.common import CheckedTable


def demographics_query(engine: Engine) -> Select:
    """Get demographic information from HIC data

    The date/time at which the data was obtained is
    not stored in the table, but patient age can be
    computed from the date of the episode under consideration
    and the year_of_birth in this table.

    The underlying table does have a cause_of_death column,
    but it is all null, so not included.

    Args:
        engine: the connection to the database

    Returns:
        SQL query to retrieve episodes table
    """
    table = CheckedTable("cv1_demographics", engine)
    return select(
        table.col("subject").label("patient_id"),
        table.col("gender"),
        table.col("year_of_birth"),
        table.col("death_date"),
    )


def episodes_query(engine: Engine, start_date: date, end_date: date) -> Select:
    """Get the episodes list in the HIC data

    This table does not contain any episode information,
    just a patient and an episode id for linking to diagnosis
    and procedure information in other tables.

    Args:
        engine: the connection to the database
        start_date: first valid consultant-episode start date
        end_date: last valid consultant-episode start date

    Returns:
        SQL query to retrieve episodes table
    """
    table = CheckedTable("cv1_episodes", engine)
    return select(
        table.col("subject").label("patient_id"),
        table.col("episode_identifier").label("episode_id"),
        table.col("spell_identifier").label("spell_id"),
        table.col("episode_start_time").label("episode_start"),
        table.col("episode_end_time").label("episode_end"),
    ).where(
        table.col("episode_start_time") >= start_date,
        table.col("episode_end_time") <= end_date,
    )


def diagnoses_query(engine: Engine) -> Select:
    """Get the diagnoses corresponding to episodes

    This should be linked to the episodes table to
    obtain information about the diagnoses in the episode.

    Diagnoses are encoded using ICD-10 codes, and the
    position column contains the order of diagnoses in
    the episode (1-indexed).

    Args:
        engine: the connection to the database

    Returns:
        SQL query to retrieve diagnoses table
    """
    table = CheckedTable("cv1_episodes_diagnosis", engine)
    return select(
        table.col("episode_identifier").label("episode_id"),
        table.col("diagnosis_date_time").label("time"),
        table.col("diagnosis_position").label("position"),
        table.col("diagnosis_code_icd").label("icd"),
    )


def procedures_query(engine: Engine) -> Select:
    """Get the procedures corresponding to episodes

    This should be linked to the episodes table to
    obtain information about the procedures in the episode.

    Procedures are encoded using OPCS-4 codes, and the
    position column contains the order of procedures in
    the episode (1-indexed).

    Args:
        engine: the connection to the database

    Returns:
        SQL query to retrieve procedures table
    """
    table = CheckedTable("cv1_episodes_procedures", engine)
    return select(
        table.col("episode_identifier").label("episode_id"),
        table.col("procedure_date_time").label("time"),
        table.col("procedure_position").label("position"),
        table.col("procedure_code_opcs").label("opcs"),
    )


def pathology_blood_query(engine: Engine, investigations: list[str]) -> Engine:
    """Get the table of blood test results in the HIC data

    Since blood tests in this table are not associated with an episode
    directly by key, it is necessary to link them based on the patient
    identifier and date. This operation can be quite slow if the blood
    tests table is large. One way to reduce the size is to filter by
    investigation using the investigations parameter. The investigation
    codes in the HIC data are shown below:

    | `investigation` | Description                 |
    |-----------------|-----------------------------|
    | OBR_BLS_UL      |                          LFT|
    | OBR_BLS_UE      |    UREA,CREAT + ELECTROLYTES|
    | OBR_BLS_FB      |             FULL BLOOD COUNT|
    | OBR_BLS_UT      |        THYROID FUNCTION TEST|
    | OBR_BLS_TP      |                TOTAL PROTEIN|
    | OBR_BLS_CR      |           C-REACTIVE PROTEIN|
    | OBR_BLS_CS      |              CLOTTING SCREEN|
    | OBR_BLS_FI      |                        FIB-4|
    | OBR_BLS_AS      |                          AST|
    | OBR_BLS_CA      |                CALCIUM GROUP|
    | OBR_BLS_TS      |                  TSH AND FT4|
    | OBR_BLS_FO      |                SERUM FOLATE|
    | OBR_BLS_PO      |                    PHOSPHATE|
    | OBR_BLS_LI      |                LIPID PROFILE|
    | OBR_POC_VG      | POCT BLOOD GAS VENOUS SAMPLE|
    | OBR_BLS_HD      |              HDL CHOLESTEROL|
    | OBR_BLS_FT      |                      FREE T4|
    | OBR_BLS_FE      |               SERUM FERRITIN|
    | OBR_BLS_GP      |    ELECTROLYTES NO POTASSIUM|
    | OBR_BLS_CH      |                  CHOLESTEROL|
    | OBR_BLS_MG      |                    MAGNESIUM|
    | OBR_BLS_CO      |                     CORTISOL|

    Each test is similarly encoded. The valid test codes in the full
    blood count and U+E investigations are shown below:

    | `investigation` | `test`     | Description          |
    |-----------------|------------|----------------------|
    | OBR_BLS_FB      | OBX_BLS_NE |           Neutrophils|
    | OBR_BLS_FB      | OBX_BLS_PL |             Platelets|
    | OBR_BLS_FB      | OBX_BLS_WB |      White Cell Count|
    | OBR_BLS_FB      | OBX_BLS_LY |           Lymphocytes|
    | OBR_BLS_FB      | OBX_BLS_MC |                   MCV|
    | OBR_BLS_FB      | OBX_BLS_HB |           Haemoglobin|
    | OBR_BLS_FB      | OBX_BLS_HC |           Haematocrit|
    | OBR_BLS_UE      | OBX_BLS_NA |                Sodium|
    | OBR_BLS_UE      | OBX_BLS_UR |                  Urea|
    | OBR_BLS_UE      | OBX_BLS_K  |             Potassium|
    | OBR_BLS_UE      | OBX_BLS_CR |            Creatinine|
    | OBR_BLS_UE      | OBX_BLS_EP | eGFR/1.73m2 (CKD-EPI)|

    Args:
        engine: the connection to the database
        investigations: Which types of laboratory
            test to include in the query. Fetching fewer types of
            test makes the query faster.

    Returns:
        SQL query to retrieve blood tests table
    """
    table = CheckedTable("cv1_pathology_blood", engine)
    return select(
        table.col("subject").label("patient_id"),
        table.col("investigation_code").label("investigation"),
        table.col("test_code").label("test"),
        table.col("test_result").label("result"),
        table.col("test_result_unit").label("unit"),
        table.col("sample_collected_date_time").label("sample_date"),
        table.col("result_available_date_time").label("result_date"),
        table.col("result_flag"),
        table.col("result_lower_range"),
        table.col("result_upper_range"),
    ).where(table.col("investigation_code").in_(investigations))
