import utils

def mock_editor(parent, init_records):
    """Mock editor using data_editor

    Returns the edit_records after user updates
    """
    initial_edit_records = utils.get_empty_edit_records(init_records) 
    initial_edit_df = utils.records_to_df(initial_edit_records)
    edit_df = parent.data_editor(initial_edit_df, key="data_editor")
    return utils.df_to_records(edit_df)
