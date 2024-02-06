# PyHBR Design

This section describes the design of PyHBR and how the code is structured.

## Data Sources and Analysis

The package contains routines for performing data analysis and fitting models. The source data for this analysis are tables stored in Microsoft SQL Server.

In order to make the models reusable, the analysis/model code expects the tables in a particular format, which is documented for each analysis/model script. The code for analysis is in the `pyhbr.analysis` module.

The database query and data fetch is performed by separate code, which is expected to be modified to port this package to a new data source. These data collection scripts are stored in the `pyhbr.data_source` module.