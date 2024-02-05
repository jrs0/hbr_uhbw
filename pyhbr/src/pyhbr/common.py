"""Common utilities for other modules
"""

import sqlalchemy as sql
import pandas as pd

def read_sql(query, con_string = "mssql+pyodbc://dsn"):
    """Connect to a database and execute a query

    This function is intended for use with Microsoft SQL
    Server. The preferred method to connect to the server
    on Windows is to use a Data Source Name. To use the
    default connection string argument, set up a data source
    name called "dsn" using the program "ODBC Data Sources."

    Any database server supported by sqlalchemy can be used
    with this function. Specify the con_string for the
    connection as described [here](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls).

    Args:
        query (str): The SQL query to execute
        con_string (str): sqlalchemy connection string

    Returns:
        (pandas.DataFrame): The result of the query
    """
    con = sql.create_engine(con_string)
    result = pd.read_sql(query, con)
    return result