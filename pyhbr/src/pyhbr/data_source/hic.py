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

