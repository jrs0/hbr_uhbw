import numpy as np
import pandas as pd
import scipy
from pyhbr import common
from pyhbr.analysis import describe
import matplotlib.pyplot as plt
import seaborn as sns

data, data_path = common.load_item("icb_hic_data")

# For convenience
outcomes = data["outcomes"]
features_index = data["features_index"]  # bool-only
features_codes = data["features_codes"]  # float-only
features_prescriptions = data["features_prescriptions"]  # float-only
features_measurements = data["features_measurements"]  # float-only
features_attributes = data["features_attributes"]  # float, category, Int8
features_secondary_prescriptions = data["features_secondary_prescriptions"]


# Check outcomes
missing_outcomes = describe.proportion_missingness(outcomes)
print("The amount of missing data in the outcome columns is:")
print(missing_outcomes)
prevalence_outcomes = describe.get_column_rates(outcomes)
print("The rate of occurrence of each outcome is:")
print(prevalence_outcomes)


# Get prevalences of all combinations of bleeding/ischaemia
# outcomes, which is used as an input to the hbr_tradeoff app
100 * pd.crosstab(outcomes["bleeding"], outcomes["ischaemia"]) / len(outcomes)

# Create a table of dataset and outcomes information
start_date = data["icb_basic_tmp"]["index_start"]
end_date = data["icb_basic_tmp"]["index_end_date"]
num_acs = len(outcomes)

fatal_bleeding = outcomes.sum().loc["fatal_bleeding"]
non_fatal_bleeding = outcomes.sum().loc["non_fatal_bleeding"]
total_bleeding = outcomes.sum().loc["bleeding"]

fatal_ischaemia = outcomes.sum().loc["fatal_ischaemia"]
non_fatal_ischaemia = outcomes.sum().loc["non_fatal_ischaemia"]
total_ischaemia = outcomes.sum().loc["ischaemia"]


# Folder in which to save plots and other data
res_folder = "../hbr_papers/resources/"

outcomes_map = {
    "Any Bleeding": f"{int(total_bleeding)} ({100*total_bleeding/num_acs:.2f}%)",
    "Fatal Bleeding": f"{int(fatal_bleeding)} ({100*fatal_bleeding/num_acs:.2f}%)",
    "Non-Fatal Bleeding": f"{int(non_fatal_bleeding)} ({100*non_fatal_bleeding/num_acs:.2f}%)",
    "Any Ischaemia": f"{int(total_ischaemia)} ({100*total_ischaemia/num_acs:.2f}%)",
    "Fatal Ischaemia": f"{int(fatal_ischaemia)} ({100*fatal_ischaemia/num_acs:.2f}%)",
    "Non-Fatal Ischaemia": f"{int(non_fatal_ischaemia)} ({100*non_fatal_ischaemia/num_acs:.2f}%)",
}
outcomes_table = pd.DataFrame(
    {"Event": outcomes_map.keys(), "Patient Count": outcomes_map.values()}
)
with open(res_folder + "outcomes.tex", "w") as f:
    f.write(outcomes_table.to_latex())

# Check prescriptions
missing_prescriptions = describe.proportion_missingness(features_prescriptions)
print("The amount of missing data in the prescriptions columns is:")
print(missing_prescriptions)
prevalence_prescriptions = describe.get_column_rates(features_prescriptions > 0)
print("The rate of occurrence of each prescriptions is:")
print(prevalence_prescriptions)

# Check measurements
missing_measurements = describe.proportion_missingness(features_measurements)
print("The amount of missing data in the measurements columns is:")
print(missing_measurements)
prevalence_prescriptions = describe.get_column_rates(features_prescriptions > 0)
print("The rate of occurrence of each prescriptions is:")
print(prevalence_prescriptions)

# Plot measurement distribution
measurement_names = {
    "bp_systolic": "Blood pressure (sys.), mmHg",
    "bp_diastolic": "Blood pressure (dia.), mmHg",
    "hba1c": "HbA1c, mmol/mol",
}
long = features_measurements.rename(columns=measurement_names).melt(
    var_name="Measurement", value_name="Result"
)
sns.displot(long, x="Result", hue="Measurement")
plt.title("Non-missing primary-care measurements (up to 2 months before index)")
plt.tight_layout()
plt.show()

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

# Check prescriptions


# Plot the distribution of polypharmacy prescription counts
polypharmacy = (
    features_attributes.filter(regex="polypharmacy")
    .rename(columns={"polypharmacy_acute": "Acute", "polypharmacy_repeat": "Repeat"})
    .melt(var_name="Prescription type", value_name="Count in attribute month")
)
sns.displot(
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
numeric_names = {
    "egfr": "eGFR",
    "polypharmacy_repeat": "Pharm. (Rep.)",
    "polypharmacy_acute": "Pharm. (Acute)",
    "bmi": "BMI",
    "alcohol_units": "Alcohol",
    "efi_category": "EFI",
}
numeric_attributes = features_attributes.select_dtypes(include="float").rename(
    columns=numeric_names
)
missing_numeric = describe.proportion_missingness(numeric_attributes).rename(
    "Percent Missingness"
)
sns.barplot(100 * missing_numeric)
plt.xticks(rotation=90)
plt.xlabel("Feature name")
plt.title("Proportion of missingness in numerical attributes")
plt.tight_layout()
plt.show()

# Plot numeric attributes
long = numeric_attributes.melt(var_name="Numeric Feature", value_name="Numeric Value")
sns.displot(long, x="Numeric Value", hue="Numeric Feature")
plt.title("Other numerical non-missing primary care attributes")
plt.tight_layout()
plt.xlim(0, 100)
plt.show()


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
long_counts["Category"] = long_counts["variable"].case_when(
    [
        (long_counts["variable"] == "Bleeding (ADAPTT)", "Outcome group"),
        (long_counts["variable"] == "AMI/Stroke", "Outcome group"),
    ]
)
sns.barplot(long, x="variable", y="value", hue="Category")
plt.xticks(rotation=90)
plt.tight_layout()
plt.title("Prevalence of Prior Code Groups before Index ACS/PCI")
plt.xlabel("Code Group")
plt.ylabel("Percentage of Index Events with Prior Code")
plt.show()
