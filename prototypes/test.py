# Create VS Code virtual env (.venv) using Python 3.11.4
#
# pip install numpy matplotlib pandas scikit-learn scikit-survival
#
# Tested on Python 3.11.4.
# 
# Python package repositories are blocked by UHBW network policies, 
# but installing python packages manually is allowed. It is easier 
# to create a virtual environment, archive it, and copy it to the 
# target computer (assuming the same python version), than to manually
# download the dependent wheels and install them one by one.
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sklearn as skl
import sksurv as sks
