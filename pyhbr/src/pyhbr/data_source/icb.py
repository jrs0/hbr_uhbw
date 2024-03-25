"""Data sources available from the BNSSG ICB

This file contains queries that fetch the raw data from the BNSSG
ICB, which includes hospital episode statistics (HES) and primary
care data.

This file does not include the HIC data transferred to the ICB.
"""

from itertools import product
from datetime import date
from sqlalchemy import select, Select, Engine, String
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
    """_summary_

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
    valid_list = ["5M8","11T","5QJ","11H","5A3","12A","15C","14F","Q65"]

    return select(*columns).where(
        table.col("StartDate_ConsultantEpisode") >= start_date,
        table.col("EndDate_ConsultantEpisode") <= end_date,
        table.col("AIMTC_Pseudo_NHS").is_not(None),
        table.col("AIMTC_Pseudo_NHS") != 9000219621, # Invalid-patient marker
        table.col("AIMTC_OrganisationCode_Codeofcommissioner").in_(valid_list),
    )

