# Create VS Code virtual env (.venv) using Python 3.11.4
#
# Python package repositories are blocked by UHBW network policies, 
# but installing python packages manually is allowed. It is easier 
# to create a virtual environment, archive it, and copy it to the 
# target computer (assuming the same python version), than to manually
# download the dependent wheels and install them one by one.
#
# On Windows, you can create a virtual environment in VS Code by
# creating a new python file (to ensure the Python extension is
# active), typing Ctrl-Shift-P, and running 
#   
#    Python: Create Environment...
#    Venv
#
# This should create a folder called .venv in the current VS Code
# folder. The environment should automatically activate (close and
# open the powershell terminal in VS Code to refresh it). To confirm
# it is active, look for `3.11.4 ('.venv': venv)` in the bottom right
# corner of the VS Code screen. If it does not activate automatically,
# type Ctrl-Shift-P and run
#
#     Python: Select Interpreter
#     < Pick the Python version from the venv >
#
# When moving a virtual environment between two computers, consider
# compressing it; the compression ratio is very good (e.g. 500 MiB to
# 100 MiB).
#
# The packages in this virtual environment were installed using:
#
#   pip install numpy matplotlib pandas scikit-learn scikit-survival
#
# The package versions are listed in requirements.txt, and the same
# versions can be installed in a new environment using 
#
#   pip install -r requirements.txt
#
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sklearn as skl
import sksurv as sks
