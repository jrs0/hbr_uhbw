from pyhbr.data_source import hic
from pyhbr.common import read_sql
import datetime as dt

# Cover all the data
start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030,1,1)

query = hic.pathology_blood_query()#episodes_query(start_date, end_date)
print(query)
df = read_sql(query)

df[df.investigation_code.isin(["OBR_BLS_UE","OBR_BLS_FB"])][["investigation_code","test_code","test_name"]].drop_duplicates()