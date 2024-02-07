# PyHBR Design

This section describes the design of PyHBR and how the code is structured.

## Data Sources and Analysis

The package contains routines for performing data analysis and fitting models. The source data for this analysis are tables stored in Microsoft SQL Server.

In order to make the models reusable, the analysis/model code expects the tables in a particular format, which is documented for each analysis/model script. The code for analysis is in the `pyhbr.analysis` module.

The database query and data fetch is performed by separate code, which is expected to be modified to port this package to a new data source. These data collection scripts are stored in the `pyhbr.data_source` module.

### SQL Queries

The approach taken to prepare SQL statements is to use SQLAlchemy to prepare a query, and then pass it to Pandas [read_sql](https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html) for execution. The advantage of using SQLAlchemy statements instead of raw strings in `read_sql` is the ability to construct statements using a declarative syntax (including binding parameters), and increased opportunity for error checking (which may be useful for porting the scripts to new databases).

An example of how SQL statements are built is shown below:

```python
from sqlalchemy import select
from pyhbr.common import make_engine, CheckedTable
import pandas as pd
import datetime as dt

# All interactions with the database (including building queries,
# which queries the server to check columns) needs an sqlalchemy 
# engine
engine = make_engine()

# The CheckedTable is a simple wrapper around sqlalchemy.Table,
# for the purpose of checking for missing columns. It replaces
# sqlalchemy syntax table.c.column_name with table.col("column_name")
table = CheckedTable("cv1_episodes", engine)

# The SQL statement is built up using the sqlalchemy select function.
# The declarative syntax reduces the chance of errors typing a raw
# SQL string. This line will throw an error if any of the columns are
# wrong.
stmt = select(
    table.col("subject").label("patient_id"),
    table.col("episode_identifier").label("episode_id"),
    table.col("spell_identifier").label("spell_id"),
    table.col("episode_start_time").label("episode_start"),
    table.col("episode_end_time").label("episode_end"),
).where(
    table.col("episode_start_time") >= dt.date(2000, 1, 1),
    table.col("episode_end_time") <= dt.date(2005, 1, 1)
)

# The SQL query can be printed for inspection if required,
# or for using directly in a SQL script
print(stmt)

# Otherwise, execute the query using pandas to get a dataframe
df = pd.read_sql(stmt, engine)
```

See the `pyhbr.data_source` module for more examples of functions that return the `stmt` variable for different tables.