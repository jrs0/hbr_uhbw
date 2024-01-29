# Create VS Code virtual env (.venv) using Python 3.11.4
#
# Python package repositories are blocked by UHBW network policies, 
# but installing python packages manually is allowed. It is easier 
# to create a virtual environment, archive it, and copy it to the 
# target computer (assuming the same python version), than to manually
# download the dependent wheels and install them one by one.
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
