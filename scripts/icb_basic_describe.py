import pandas as pd
from pyhbr import common
from pyhbr.analysis import describe
import matplotlib.pyplot as plt
import seaborn as sns

icb_basic_data = common.load_item("icb_basic_data")

# Get datasets for convenience
outcomes = icb_basic_data["outcomes"]
features_attributes = icb_basic_data["features_attributes"]

# Check outcomes
missing_outcomes = describe.proportion_missingness(outcomes)
print("The amount of missing data in the outcome columns is:")
print(missing_outcomes)
prevalence_outcomes = describe.get_column_rates(outcomes)
print("The rate of occurrence of each outcome is:")
print(prevalence_outcomes)

# Check raw attributes


# Check attributes
missing_attributes = describe.proportion_missingness(features_attributes)
print("The amount of missing data in the attributes columns is:")
print(missing_attributes)


numeric_attributes = features_attributes.select_dtypes(include="number").iloc[:,0:16].melt()
sns.catplot(numeric_attributes, y="value", kind="box", col="variable", col_wrap=8, sharey=False)
plt.show()


#.boxplot(meanline=True, showmeans=True)
#plt.show()
