def diagnosis_and_procedure_columns():
    """BNSSG ICB diagnosis/procedure column names

    Get the diagnosis and procedure part of the
    SQL query, which is common to both the episodes and
    spells queries. 
    
    Column names are mapped to the names diagnosis_n,
    procedure_n, where n is zero-indexed. The primary
    diagnosis/procedure is diagnosis_0/procedure_0, and
    smaller n implies higher diagnosis/procedure priority.

    Returns:
        (str): part of SQL select query listing diagnosis/procedure columns
    """
    return (
        ",diagnosisprimary_icd as diagnosis_0"
        ",diagnosis1stsecondary_icd as diagnosis_1"
        ",diagnosis2ndsecondary_icd as diagnosis_2"
        ",diagnosis3rdsecondary_icd as diagnosis_3"
        ",diagnosis4thsecondary_icd as diagnosis_4"
        ",diagnosis5thsecondary_icd as diagnosis_5"
        ",diagnosis6thsecondary_icd as diagnosis_6"
        ",diagnosis7thsecondary_icd as diagnosis_7"
        ",diagnosis8thsecondary_icd as diagnosis_8"
        ",diagnosis9thsecondary_icd as diagnosis_9"
        ",diagnosis10thsecondary_icd as diagnosis_10"
        ",diagnosis11thsecondary_icd as diagnosis_11"
        ",diagnosis12thsecondary_icd as diagnosis_12"
        ",diagnosis13thsecondary_icd as diagnosis_13"
        ",diagnosis14thsecondary_icd as diagnosis_14"
        ",diagnosis15thsecondary_icd as diagnosis_15"
        ",diagnosis16thsecondary_icd as diagnosis_16"
        ",diagnosis17thsecondary_icd as diagnosis_17"
        ",diagnosis18thsecondary_icd as diagnosis_18"
        ",diagnosis19thsecondary_icd as diagnosis_19"
        ",diagnosis20thsecondary_icd as diagnosis_20"
        ",diagnosis21stsecondary_icd as diagnosis_21"
        ",diagnosis22ndsecondary_icd as diagnosis_22"
        ",diagnosis23rdsecondary_icd as diagnosis_23"
        ",primaryprocedure_opcs as procedure_0"
        ",procedure2nd_opcs as procedure_1"
        ",procedure3rd_opcs as procedure_2"
        ",procedure4th_opcs as procedure_3"
        ",procedure5th_opcs as procedure_4"
        ",procedure6th_opcs as procedure_5"
        ",procedure7th_opcs as procedure_6"
        ",procedure8th_opcs as procedure_7"
        ",procedure9th_opcs as procedure_8"
        ",procedure10th_opcs as procedure_9"
        ",procedure11th_opcs as procedure_10"
        ",procedure12th_opcs as procedure_11"
        ",procedure13th_opcs as procedure_12"
        ",procedure14th_opcs as procedure_13"
        ",procedure15th_opcs as procedure_14"
        ",procedure16th_opcs as procedure_15"
        ",procedure17th_opcs as procedure_16"
        ",procedure18th_opcs as procedure_17"
        ",procedure19th_opcs as procedure_18"
        ",procedure20th_opcs as procedure_19"
        ",procedure21st_opcs as procedure_20"
        ",procedure22nd_opcs as procedure_21"
        ",procedure23rd_opcs as procedure_22"
        ",procedure24th_opcs as procedure_23"
    )

def episodes_query(start_date, end_date):
    """BNSSG ICB SQL query for episodes table

    Make an SQL query to retrieve the episodes table
    between start_date and end_date (inclusive).

    Notes:
    
    The NHS number 9000219621 is used to indicate
    "invalid NHS number" in these tables, so should
    be excluded.
    
    Rows with the following commissioner codes are
    not valid: '5M8','11T','5QJ','11H','5A3','12A',
    '15C','14F','Q65'.
    
    The nhs_number not-NULL condition ensures that
    the columns will not be converted to floating 
    point by pandas.

    Args:
        start_date (datetime.date): first valid consultant-episode start date
        end_date (datetime.date): last valid consultant-episode start date

    Returns:
        (str): SQL query to retrieve episodes table
    """
    return (
        "select aimtc_pseudo_nhs as patient_id"
        ",aimtc_age as age"
        ",sex as gender"
        ",pbrspellid as spell_id"
        ",aimtc_providerspell_start_date as spell_start_date"
        ",aimtc_providerspell_end_date as spell_end_date"
        ",startdate_consultantepisode as episode_start_date"
        ",enddate_consultantepisode as episode_end_date"
        + diagnosis_and_procedure_columns()
        + " from abi.dbo.vw_apc_sem_001"
        f" where startdate_consultantepisode between '{start_date}' and '{end_date}'"
        " and aimtc_pseudo_nhs is not null"
        " and aimtc_pseudo_nhs != '9000219621'"
        " and aimtc_organisationcode_codeofcommissioner in ('5M8','11T','5QJ','11H','5A3','12A','15C','14F','Q65')"
    )