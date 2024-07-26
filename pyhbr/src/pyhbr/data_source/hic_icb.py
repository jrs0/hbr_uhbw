"""SQL queries and functions for HIC (ICB version)

Most data available in the HIC tables is fetched in the 
queries below, apart from columns which are all-NULL,
provide keys/IDs that will not be used, or provide duplicate
information (e.g. duplicated in two tables). 

Note that the lab results/pharmacy queries are in the
hic.py module, because there are no changes to the query
apart from the table name.
"""

from datetime import date
from sqlalchemy import select, Select, Engine, String
from pyhbr.common import CheckedTable

def episode_id_query(engine: Engine) -> Select:
    """Get the episodes list in the HIC data

    This table is just a list of IDs to identify the data in other ICB tables.

    Args:
        engine: the connection to the database

    Returns:
        SQL query to retrieve episodes table
    """
    table = CheckedTable("hic_episodes", engine)
    return select(
        table.col("nhs_number").cast(String).label("patient_id"),
        table.col("episode_identified").cast(String).label("episode_id"),
    )
    

def pathology_blood_query(engine: Engine, test_names: list[str]) -> Engine:
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
        test_names: Unlike the UHBW version of this table, there are no
            investigation names here. Instead, restrict directly using
            the test_name field.

    Returns:
        SQL query to retrieve blood tests table
    """
    
    table = CheckedTable("HIC_BLoods", engine)
    return select(
        table.col("nhs_number").cast(String).label("patient_id"),
        table.col("test_name"),
        table.col("test_result").label("result"),
        table.col("test_result_unit").label("unit"),
        table.col("sample_collected_date_time").label("sample_date"),
        table.col("result_available_date_time").label("result_date"),
        table.col("result_lower_range"),
        table.col("result_upper_range"),
    ).where(table.col("test_name").in_(test_names))