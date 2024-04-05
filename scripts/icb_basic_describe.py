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
sns.barplot(missing_attributes)
plt.xticks(rotation=90)
plt.title("Proportion of missing attributes (> 70\% excluded)")
plt.tight_layout()
plt.show()

# Plot the distribution of polypharmacy prescription counts
polypharmacy = (
    features_attributes.filter(regex="polypharmacy")
    .rename(columns={"polypharmacy_acute": "Acute", "polypharmacy_repeat": "Repeat"})
    .melt(var_name="Prescription type", value_name="Count in attribute month")
)
sns.histplot(polypharmacy, x="Count in attribute month", hue="Prescription type", stat="percent", multiple="dodge")
plt.title("Distribution of prescription counts in non-missing rows")
plt.show()

# Plot the egfr (if present). Seem to be a lot of zeros (note zero does
# not mean NA). The large distribution at about 100 means eGFR > 90, which 
# can be recorded as 90 in the data, and represents the tail of the distribution.
egfr = features_attributes["egfr"].rename("eGFR (mL/min)")
sns.displot(egfr, stat="percent")
plt.title("Distribution of eGFR in non-missing rows")
plt.tight_layout()
plt.show()

# Plot some of these individually
numeric_attributes = features_attributes.select_dtypes(include="number")

# Each is True/False/NaN (note, represented as object because bool
# cannot store NaN)
flag_attributes = features_attributes.select_dtypes(exclude="number")
long = flag_attributes.melt()
sns.barplot(long, x = "variable", y = "value")
plt.show()

