def get_records(init_records, edit_records):
    """Get the summary records that will be printed

    This involves overwriting the init_data with edit_data
    if it is present, and storing a flag to indicate that
    the data was edited
    """

    summary_records = {}
    for t_number, init_record in init_records.items():
        edit_record = edit_records[t_number]

        summary_record = {}
        for key, value in init_record.items():

            if edit_record[key] is None:
                summary_record[key] = value
                summary_record[f"{key}_edited"] = False
            else:
                summary_record[key] = edit_record[key]
                summary_record[f"{key}_edited"] = True

        summary_records[t_number] = summary_record

    return summary_records
