from pyhbr.data_source import hic
from pyhbr.common import read_sql
import datetime as dt

# Cover all the data
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030,1,1)

query = hic.demographics_query()#episodes_query(start_date, end_date)
print(query)
df = read_sql(query)