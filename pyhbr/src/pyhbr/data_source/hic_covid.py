"""SQL queries and functions for HIC (COVID-19, UHBW) data.
"""

from sqlalchemy import select, Select, Engine, String
from pyhbr.common import CheckedTable

def episodes_query(engine: Engine) -> Select:
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
    table = CheckedTable("cv_covid_episodes", engine)
    return select(
        table.col("NHS_NUMBER").cast(String).label("nhs_number"),
        table.col("Other Number").cast(String).label("t_number"),
        table.col("episode_identifier").cast(String).label("episode_id"),
    )
