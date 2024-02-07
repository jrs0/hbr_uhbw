"""Common utilities for other modules.

A collection of routines used by the data source or analysis functions.
"""

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import NoSuchTableError
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

class CheckedTable:
    def __init__(self, table_name, engine):
        """Get a CheckedTable by reading from the remote server

        This is a wrapper around the sqlalchemy Table for 
        catching errors when accessing columns through the
        c attribute.
        
        Args:
            table (str): The table name to get
            engine (sqlalchemy.Engine): The database connection 

        Returns:
            (CheckedTable): The table data for use in SQL queries
        """
        self.name = table_name
        metadata_obj = MetaData()
        try:
            self.table = Table(self.name, metadata_obj, autoload_with=engine)
        except NoSuchTableError as e:
            raise RuntimeError(f"Could not find table '{e}' in database connection '{engine.url}'")

    def c(self)
        try:
            self.table.c
            table.c.investigation_code.label("investigation"),
            table.c.test_code.label("test"),
            table.c.test_result.label("result"),
            table.c.test_result_unit.label("unit"),
            table.c.sample_collected_date_time.label("sample_date"),
            table.c.result_available_date_time.label("result_date"),
            table.c.result_flag,
            table.c.result_lower_range,
            table.c.result_upper_range
        ).where(table.c.investigation_code.in_(investigations))
        return stmt
    except AttributeError as e:
        raise RuntimeError(f"Could not find column name '{e}' in table '{table_name}'")


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