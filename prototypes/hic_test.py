from pyhbr.common import make_engine, get_data
from pyhbr.data_source import hic
import pandas as pd
import datetime as dt

# Cover all the data
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

demographics_query = get_data(engine, hic.demographics_query)
episodes_df = get_data(engine, hic.episodes_query, start_date, end_date)
diagnoses_df = get_data(engine, hic.diagnoses_query)
procedures_df = get_data(engine, hic.procedures_query)
pathology_blood_df = get_data(engine, hic.pathology_blood_query)
