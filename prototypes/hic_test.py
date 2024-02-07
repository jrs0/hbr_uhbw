# from pyhbr.data_source import hic
# from pyhbr.common import read_sql
# import datetime as dt

# # Cover all the data
# start_date = dt.date(1990, 1, 1)
# end_date = dt.date(2030,1,1)

# query = hic.demographics_query() # pathology_blood_query()#episodes_query(start_date, end_date)
# print(query)
# df = read_sql(query)

from sqlalchemy import create_engine, Table, MetaData

connect_args = { "database": "hic_cv_test"}
engine = create_engine("mssql+pyodbc://dsn", connect_args=connect_args)
metadata_obj = MetaData()
Table("cv1_demographics", metadata_obj, autoload_with=engine)