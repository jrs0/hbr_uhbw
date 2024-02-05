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

    Args:
        query (str): The SQL query to execute
        con_string (str)): sqlalchemy connection string

    Returns:
        pandas dataframe: The result of the query (table)
    """
    con = sql.create_engine(con_string)
    result = pd.read_sql(query, con)
    return result