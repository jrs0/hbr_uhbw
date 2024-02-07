from pyhbr.common import make_engine
from pyhbr.data_source import hic
import pandas as pd
import datetime as dt

# Cover all the data
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030,1,1)

# query = hic.demographics_query() # pathology_blood_query()#episodes_query(start_date, end_date)
# print(query)
# df = read_sql(query)

engine = make_engine()
stmt = hic.demographics_query(engine)
print(stmt)
df = pd.read_sql(stmt, engine)

