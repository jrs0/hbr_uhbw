"""Convert HIC tables into the formats required for analysis
"""

import pandas as pd
from sqlalchemy import Engine
from pyhbr.clinical_codes import ClinicalCodeTree, codes_in_any_group, normalise_code, load_from_package
from pyhbr.common import get_data
from pyhbr.data_source import hic

def filter_to_groups(codes_table: pd.DataFrame, codes: ClinicalCodeTree) -> pd.DataFrame:
    """Filter a table of raw clinical codes to only keep codes in groups

    Use this function to drop clinical codes which are not of interest, 
    and convert all codes to normalised form (lowercase, no whitespace, no dot).

    This function is tested on the HIC dataset, but should be modifiable
    for use with any data source returning diagnoses and procedures as
    separate tables in long format. Consider modifying the columns of
    codes_table that are contained in the output.
    
    Args:
        codes_table: Either a diagnoses or procedures table. For this
            function to work, it needs:

            * A `code` column containing the clinical code.
            * An `episode_id` identifying which episode contains the code.
            * A `position` identifying the primary/secondary position of the
                code in the episode.
        
        codes: The clinical codes object (previously loaded from a file)
            containing code groups to use.

    Returns:
        A table containing the episode ID, the clinical code (normalised),
        the group containing the code, and the code position.

    """
    codes_with_groups = codes_in_any_group(codes)
    codes_table["code"] = codes_table["code"].apply(normalise_code)
    codes_table = pd.merge(codes_table, codes_with_groups, on="code", how="inner")
    codes_table = codes_table[["episode_id", "code", "group", "position"]]

    return codes_table

def get_clinical_codes(engine: Engine, diagnoses_file: str, procedures_file: str) -> pd.DataFrame:
    """Main diagnoses/procedures fetch for the HIC data

    This function wraps the diagnoses/procedures queries and a filtering
    operation to reduce the tables to only those rows which contain a code
    in a group. One table is returned which contains both the diagnoses and
    procedures in long format, along with the associated episode ID and the
    primary/secondary position of the code in the episode.

    Args:
        engine: the connection to the database
        diagnoses_file: The diagnoses codes file name (loaded from the package)
        procedures_file: The procedures codes file name (loaded from the package)

    Returns:
        A table containing diagnoses/procedures, normalised codes, code groups,
            diagnosis positions, and associated episode ID.
    """

    diagnosis_codes = load_from_package(diagnoses_file)
    procedures_codes = load_from_package(procedures_file)

    # Fetch the data from the server
    diagnoses = get_data(engine, hic.diagnoses_query)
    procedures = get_data(engine, hic.procedures_query)

    # Reduce data to only code groups, and combine diagnoses/procedures
    filtered_diagnoses = filter_to_groups(diagnoses, diagnosis_codes)
    filtered_procedures = filter_to_groups(procedures, procedures_codes)

    # Tag the diagnoses/procedures, and combine the tables
    filtered_diagnoses["type"] = "diagnoses"
    filtered_procedures["type"] = "procedures"
    return pd.concat([filtered_diagnoses, filtered_procedures])