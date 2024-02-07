# from pyhbr.data_source import hic
# from pyhbr.common import read_sql
# import datetime as dt

# # Cover all the data
# start_date = dt.date(1990, 1, 1)
# end_date = dt.date(2030,1,1)

# query = hic.demographics_query() # pathology_blood_query()#episodes_query(start_date, end_date)
# print(query)
# df = read_sql(query)

from sqlalchemy import Table, MetaData, select
from pyhbr.common import make_engine
import pandas as pd

engine = make_engine()

metadata_obj = MetaData()
table = Table("cv1_demographics", metadata_obj, autoload_with=engine)
stmt = select(table.c.subject.label("patient_id"))
df = pd.read_sql(stmt, engine)

