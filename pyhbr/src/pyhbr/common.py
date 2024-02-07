"""Common utilities for other modules.

A collection of routines used by the data source or analysis functions.
"""

from sqlalchemy import create_engine
import pandas as pd

def make_engine(con_string = "mssql+pyodbc://dsn", database = "hic_cv_test"):
    """Make a sqlalchemy engine

    This function is intended for use with Microsoft SQL
    Server. The preferred method to connect to the server
    on Windows is to use a Data Source Name (DSN). To use the
    default connection string argument, set up a data source
    name called "dsn" using the program "ODBC Data Sources".

    If you need to access multiple different databases on the
    same server, you will need different engines. Specify the 
    database name while creating the engine (this will override
    a default database in the DSN, if there is one).

    Args:
        con_string (str, optional): The sqlalchemy connection string.
            Defaults to "mssql+pyodbc://dsn".
        database (str, optional): The database name to connect to.
            Defaults to "hic_cv_test".

    Returns:
        (sqlalchemy.engine): The sqlalchemy engine 
    """
    connect_args = { "database": database}
    return create_engine(con_string, connect_args=connect_args)

def read_sql(query, ):
    """Connect to a database and execute a query



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