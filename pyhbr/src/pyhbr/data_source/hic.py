"""SQL queries and functions for HIC (UHBW) data.
"""

def episodes_query(start_date, end_date):
    return (
        "select subject as patient_id"
        ",spell_identifier as spell_id"
        ",episode_identifier as episode_id"
        ",episode_start_time as episode_start"
        ",episode_end_time as episode_end"
        " from hic_cv_test.dbo.cv1_episodes"
        f" where episode_start_time between '{start_date}' and '{end_date}'"
    )

