import numpy as np
import pandas as pd
from pyhbr import common
from pyhbr.analysis import describe
import matplotlib.pyplot as plt
import seaborn as sns

icb_basic_data = common.load_item("icb_basic_data")

# Get datasets for convenience
outcomes = icb_basic_data["outcomes"]
features_attributes = icb_basic_data["features_attributes"]
features_codes = icb_basic_data["features_codes"]

# Check outcomes
missing_outcomes = describe.proportion_missingness(outcomes)
print("The amount of missing data in the outcome columns is:")
print(missing_outcomes)
prevalence_outcomes = describe.get_column_rates(outcomes)
print("The rate of occurrence of each outcome is:")
print(prevalence_outcomes)

# Check raw attributes (e.g. no attributes at all vs. no attributes before index)

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
sns.histplot(
    polypharmacy,
    x="Count in attribute month",
    hue="Prescription type",
    stat="percent",
    multiple="dodge",
)
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

# Each is True/False/NaN (note, represented as Int8 because bool
# cannot store NaN)
flag_attributes = features_attributes.select_dtypes(include="Int8")
long = flag_attributes.melt()
long["Present"] = (
    long["value"]
    .map(
        {
            0: "False",
            1: "True",
        }
    )
    .fillna("Missing")
)
sns.displot(long, x="variable", hue="Present", multiple="stack")
plt.xticks(rotation=90)
plt.title("Proportion of missing attributes (> 70\% excluded)")
plt.tight_layout()
plt.show()

# Code group names
code_group_names = {
    "bavm_before": "bAVM",
    "bleeding_barc_before": "Bleeding (BARC)",
    "ich_before": "ICH",
    "portal_hypertension_before": "Portal Hyp.",
    "packed_red_cells_transfusion_before": "Transfusion",
    "liver_cirrhosis_before": "Liver cirrhosis",
    "ischaemic_stroke_before": "Ischaemic stroke",
    "bleeding_adaptt_before": "Bleeding (ADAPTT)",
    "diabetes_type1_before": "Diabetes (Type 1)",
    "mi_stemi_schnier_before": "MI (STEMI)",
    "bleeding_al_ani_before": "Bleeding (al Ani)",
    "diabetes_before": "Diabetes (Any)",
    "diabetes_type2_before": "Diabetes (Type 2)",
    "mi_schnier_before": "MI (Any)",
    "ihd_bezin_before": "IHD",
    "hussain_ami_stroke_before": "AMI/stroke",
    "ckd_before": "CKD",
    "cancer_before": "Cancer (Any)",
    "pci_before": "PCI",
    "bleeding_cadth_before": "Bleeding (Cadth)",
    "acs_bezin_before": "Prior ACS",
    "mi_nstemi_schnier_before": "MI (NSTEMI)",
}

# Show the distribution of different code groups before the index
long_counts = (
    (features_codes > 0)
    .rename(columns=code_group_names)
    .melt()
    .groupby("variable")
    .sum()
    .sort_values("value")
    .reset_index()
)
long_counts["Category"] = "None"
long_counts["Category"] = long_counts["variable"].case_when([
    (long_counts["variable"] == "Bleeding (ADAPTT)", "Outcome group"),
    (long_counts["variable"] == "AMI/Stroke", "Outcome group"),    
])
sns.barplot(long, x="variable", y="value", hue="Category")
plt.xticks(rotation=90)
plt.tight_layout()
plt.title("Prevalence of Prior Code Groups before Index ACS/PCI")
plt.xlabel("Code Group")
plt.ylabel("Percentage of Index Events with Prior Code")
plt.show()
