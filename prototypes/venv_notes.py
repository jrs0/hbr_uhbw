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
# After copying to the new computer, change the following variables:
#
#    .venv/Scripts/activate: change VIRTUAL_ENV to point to the new
#         location of the virtual environment (use quotes if the path
#         has spaces)
#    .venv/pyvenv.cfg: change all the variables to match the paths to
#         python on the new computer.
#
# On UHBW trust computer, loading a virtual environment using powershell
# results in an error: ".venv\Scripts\Activate.ps1 cannot be loaded because 
# running scripts is disabled on this system." IT advised this is a 
# powershell-specific issue; changing the VS code default terminal to
# bash (e.g. git bash) solves the problem. You can change your default
# terminal using Ctrl-Shift-P, and running (make sure git bash in installed
# first):
#
#    Terminal: Select Default Profile
#    <pick Git Bash>
#
# If more packages need to be installed later, copy the .venv/Lib folder
# (containing the site-packages), as an alternative to copying the whole
# .venv again. This avoids the need to update the environment variables
# twice.
#
# The packages in this virtual environment were installed using:
#
#   pip install numpy matplotlib pandas scikit-learn scikit-survival \
#       sqlalchemy scipy imbalanced-learn pytest argparse wheel \
#       setuptools hatchling setuptools-scm[toml]
#
# (Note: the setuptools-scm[toml] is to fix what looks like a dependency
# bug in xlsx2csv, where pip freeze does not correctly record the dependency)
#
# The package versions are listed in requirements.txt, and the same
# versions can be installed in a new environment using 
#
#   pip install -r requirements.txt
#
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sqlalchemy
import sklearn as skl
import sksurv as sks
import polars as pl

# This is a better way:
#
# -1: Make a venv and install all the packages you need
# 0. pip freeze --all > prototypes/requirements.txt
# 1. pip download -r requirements.txt -d packages
# 1b. Download pip and wheel wheels and add them to 
#     the packages folder
# 2. Zip the packages folder and transfer to other computer
# 3. On computer with PyPi access, download latest pip
#    wheel, and move to other computer
# 4. On new computer, run python -m venv .venv (note: not python3;
#    on Windows, Python 3 executable is called python)
# 5. Run this line: python -m pip install --no-index --find-links packages -r prototypes/requirements.txt
#    The key points here are --no-index (do not use PyPi) and --find-links (path to the wheels).
# 