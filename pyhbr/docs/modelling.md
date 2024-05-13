# Bleeding/Ischaemia Risk Modelling

Bleeding and ischaemia risk prediction models using PyHBR are trained to predict a bleeding and ischaemia outcome defined by clinical codes (ICD-10 and OPCS-4), and are trained on a number of different datasets. The methods used to develop and test the models is explained below.

## Data Sources

Index events and outcomes are determined from diagnosis (ICD-10) and procedure (OPCS-4) codes in Hospital Episode Statistics (HES) data.

In HES, hospital visits are structured into groups of episodes called spells, where each episode corresponds to a continuous period of care (usually) led by one consultant. Each consultant episode contains a list of diagnoses and procedures. Of these, one diagnosis and one procedure is marked as primary.

The clinical coding guidelines[@nhse2023clincodestandards] define the use of the primary diagnosis field in DGCS.1:

!!! quote "Definition of Primary Diagnosis (extract from DGCS.1)"

    1. The first diagnosis field(s) of the coded clinical record (the primary diagnosis) will contain
    the main condition treated or investigated during the relevant episode of healthcare.
    2. Where a definitive diagnosis has not been made by the responsible clinician the main
    symptom, abnormal findings, or problem should be recorded in the first diagnosis field of the
    coded clinical record.

The primary diagnosis is not necessary the main clinical diagnosis; instead, it is the main diagnosis being treated in the current episode[@noa2017clincode]. Secondary diagnoses are other diagnoses relevant to the current episode, but which are not the primary diagnosis.

!!! note

    Secondary diagnoses may contain historical diagnoses if they are relevant to the current episode.

Similarly, the primary procedure is defined as the main procedure that occurred in the episode[@nhse2024clincodestandardsopcs]:

!!! quote "Definition of Primary Procedure (extract from PRule 2)"

    When classifying diagnostic information, the International Classification of Diseases and
    Health Related Problems (ICD) recommend criteria for the selection of the MAIN condition
    for single-cause analysis. OPCS-4 follows this precedent in that the intervention selected
    for single procedure analysis from records of episodes of hospital care should be the MAIN
    intervention or procedure carried out during the relevant episode which may not always be
    the first procedure performed during the consultant episode.

Secondary procedures are other interventions that occurred in the consultant episode.

## Index Events

The target cohort for risk prediction is patients who present in hospital with an acute coronary syndrome (ACS), or receive a percutaneous coronary intervention (PCI), such as a stent implant; these groups are likely to be placed on a blood thinning medication such as dual antiplatelet therapy. 

To capture acute presentation for ACS, patients are included if the ACS diagnosis is listed as the primary diagnosis in any episode of the spell. This is to rule out episodes where a historical ACS is coded. A PCI is allowed in any primary or secondary position, on the assumption that inclusion of the procedure means that the procedure was performed.

A UK Biobank report identifies a validated group of codes for identification of MI (both STEMI and NSTEMI) based on HES data, with PPV greater than 70% for each group[@biobankdefinitions]. However, the codes contain I25.2 (old myocardial infarction), which would capture patients in index events who do not necessarily have ACS at that time. This issue was addressed in a study validating ACS code groups in a French administrative database [@bezin2015choice]. Of the different code groups they present, the I20.0, I21.* and I24.* was identified as a good compromise between validated ACS and PPV (84%).

ALL OPCS-4 PCI codes are included, based on the list provided in Pathak et al. (2023).

The code groups used to define the index event are shown below:

??? note "List of ACS and PCI codes used to define index events"

    | Category | ICD-10 | Description |
    |----------|--------|-------------|
    | ACS | I20.0 | Unstable angina|  
    ||I21.*  | Acute myocardial infarction |
    ||I24.* | Other acute ischaemic heart diseases |
    |PCI|K49.* |Transluminal balloon angioplasty of coronary artery |
    ||K50.*|Other therapeutic transluminal operations on coronary artery |
    ||K75.*|Percutaneous transluminal balloon angioplasty and insertion of stent into coronary artery|

## Outcome Definition

Bleeding and ischaemia outcomes are defined by looking for ICD-10 codes in the spells that occur after the index presentation, up to one year.

### Bleeding Outcome

The bleeding outcome definition should map to a clinically relevant definition of bleeding for patients on anticoagulant therapy. One such definition is bleeding academic research consortium (BARC) 3 or 5 bleeding[@mehran2011standardized], which is the basis of the high bleeding risk definition by the Academic Research Consortium (ARC)[@urban2019defining].

Many ICD-10-coded bleeding events may qualify for BARC-2, because being written explicitly in the patient notes (a criterion for coding) could imply that an "overt" bleed is present, or that the bleed is "more than would be expected for the clinical circumstance". 

Determining that a bleed qualifies for BARC-3 requires a haemoglobin drop due to the bleed of greater than 3 g/dL. This cannot be determined from an analysis of ICD-10 codes alone. 

Several attempts to capture "severe" bleeding from administrative codes exist in the literature. For example, one study identifies a group of ICD-10 codes with a particularly high positive predictive value (PPV; chance that a ICD-10-coded bleed is in fact a clinically relevant bleed), of 88%[@al2015identifying]. The list of ICD-10 codes is shown below:

??? note "List of major bleeding codes[@al2015identifying]"

    | Description | ICD-10CM Codes |
    |-------------|--------|
    | Subarachnoid hemorrhage |I60 |
    | Intracranial hemorrhage |I61 |
    | Subdural hemorrhage | I62 |
    | Upper gastrointestinal bleeding |  I85.0, K22.1, K22.6, K25.0, K25.2, K25.4, K25.6,K26.0, K26.2, K26.4, K26.6, K27.0, K27.2, K27.4,K27.6, K28.0, K28.2, K28.4, K28.6, K29.0, K31.80,K63.80, K92.0, K92.1, K92.2 |
    | Lower gastrointestinal bleeding |  K55.2, K51, K57, K62.5, K92.0, K92.1, K92.2 |

    This groups has been interpreted as the following set of (UK) ICD-10 codes:

    | ICD-10 | Description |
    |-------------|--------|
    | I60 | Subarachnoid haemorrhage |
    | I61 | Intracerebral haemorrhage |
    | I62 | Other nontraumatic intracranial haemorrhage |
    | I85.0 | Oesophageal varices with bleeding |
    | K22.1 | Ulcer of oesophagus |
    | K22.6 | Gastro-oesophageal laceration-haemorrhage syndrome |
    | K25.0 | Gastric ulcer : acute with haemorrhage |
    | K25.2 | Gastric ulcer : acute with both haemorrhage and perforation |
    | K25.4 | Gastric ulcer : chronic or unspecified with haemorrhage |
    | K25.6 | Gastric ulcer : chronic or unspecified with both haemorrhage and perforation |
    | K26.0 | Duodenal ulcer : acute with haemorrhage |
    | K26.2 | Duodenal ulcer : acute with both haemorrhage and perforation |
    | K26.4 | Duodenal ulcer : chronic or unspecified with haemorrhage |
    | K26.6 | Duodenal ulcer : chronic or unspecified with both haemorrhage and perforation |
    | K27.0 | Peptic ulcer, site unspecified : acute with haemorrhage |
    | K27.2 | Peptic ulcer, site unspecified : acute with both haemorrhage and perforation |
    | K27.4 | Peptic ulcer, site unspecified : chronic or unspecified with haemorrhage |
    | K27.6 | Peptic ulcer, site unspecified : chronic or unspecified with both haemorrhage and perforation |
    | K28.0 | Gastrojejunal ulcer : acute with haemorrhage |
    | K28.2 | Gastrojejunal ulcer : acute with both haemorrhage and perforation |
    | K28.4 | Gastrojejunal ulcer : chronic or unspecified with haemorrhage |
    | K28.6 | Gastrojejunal ulcer : chronic or unspecified with both haemorrhage and perforation |
    | K29.0 | Acute haemorrhagic gastritis |
    | K92.0 | Haematemesis |
    | K92.1 | Melaena |
    | K92.2 | Gastrointestinal haemorrhage, unspecified |
    | K55.2 | Angiodysplasia of colon |
    | K51 | Ulcerative colitis |
    | K57 | Diverticular disease of intestine |
    | K62.5 | Haemorrhage of anus and rectum |

The primary rationale for adopting such a code group would be that:

* It originates from a study where the PPV of the code group was measured (offsetting the risk that coded bleeding definitions do not correspond to real bleeds);
* The study qualifies the group as "major" bleeds (so that it might be taken as a reasonable proxy for BARC 3 or 5 bleeding).

Disadvantages, however, include differences in coding between the UK and Canada (the location of the study), particularly the difference between ICD-10 (UK) and ICD-10CM (Canada). In addition, the presence of unqualified diverticulosis within the bleeding group is not directly a bleeding condition, and may significantly reduce the PPV in older patients.

As a result, we define a bleeding outcome based on the BARC 2-5 criteria[@pufulete2019comprehensive].

??? note "Bleeding codes corresponding to BARC 2-5"

    | Category | ICD-10 | Description |
    |----------|--------|-------------|
    | Gastrointestinal | I85.0 |Oesophageal varices with bleeding |  
    ||K25.0 | Gastric ulcer, acute with haemorrhage |
    ||K25.2 |Gastric ulcer, acute with both haemorrhage and perforation |
    ||K25.4 |Gastric ulcer, chronic or unspecified with haemorrhage |
    ||K25.6 |Chronic or unspecified with both haemorrhage and perforation |
    ||K26.0 |Duodenal ulcer, acute with haemorrhage |
    ||K26.2 |Duodenal ulcer, acute with both haemorrhage and perforation |
    ||K26.4 |Duodenal ulcer, chronic or unspecified with haemorrhage |
    ||K26.6 |Chronic or unspecified with both haemorrhage and perforation |
    ||K27.0 |Peptic ulcer, acute with haemorrhage |
    ||K27.2 |Peptic ulcer, acute with both haemorrhage and perforation |
    ||K27.4 |Peptic ulcer, chronic or unspecified with haemorrhage |
    ||K27.6 |Chronic or unspecified with both haemorrhage and perforation |
    ||K28.0 |Gastrojejunal ulcer, acute with haemorrhage |
    ||K28.2 |Acute with both haemorrhage and perforation |
    ||K28.4 |Gastrojejunal ulcer, chronic or unspecified with haemorrhage |
    ||K28.6 |Chronic or unspecified with both haemorrhage and perforation |
    ||K29.0 |Acute haemorrhagic gastritis |
    ||K62.5 |Haemorrhage of anus and rectum |
    ||K66.1 |Haemoperitoneum |
    ||K92.0 |Haematemesis |
    ||K92.1 |Melaena |
    ||K92.2 |Gastrointestinal haemorrhage, unspecified |
    |Intracerebral |I60.* |Subarachnoid haemorrhage |
    ||I61.* |Intracerebral haemorrhage |
    ||I62.* |Other nontraumatic intracranial haemorrhage |
    ||I69.0 |Sequelae of subarachnoid haemorrhage |
    ||I69.1 |Sequelae of intracerebral haemorrhage |
    ||I69.2 |Sequelae of other nontraumatic intracranial haemorrhage |
    ||S06.4 |Epidural haemorrhage |
    |Genitourinary |N93.8 |Other specified abnormal uterine and vaginal bleeding |
    ||N93.9 |Abnormal uterine and vaginal bleeding, unspecified |
    |Other |R04.* | Haemorrhage from respiratory passages |
    ||I23.0 |Haemopericardium as current complication following acute myocardial infarction |

The group is generated based on UK ICD-10 data, which is likely to reduce coding discrepancies, and does not contain the generic diverticulosis category. 

No PPV is available for this code group. A basic chart review should be performed on the patients identified by this bleeding group to increase confidence that they match relevant bleeding events.

A spell is considered to be a bleeding outcome if any episode of the spell contains a bleeding code in the primary position.

Fatal bleeding (BARC 5) is included in the bleeding outcome. Mortality information is available from the Civil Registration of Deaths, which includes a primary cause of death and multiple secondary causes of death. A death is included in the bleeding outcome when the primary cause of death (an ICD-10 code) is an ADAPTT bleeding code as described above.

### Ischaemia Outcome

Various definitions of ischaemia outcomes are commonly used when deriving outcomes from administrative databases[@bosco2021major]. We require a definition of major adverse cardiovascular event (MACE) that uses ICD-10 codes, and includes only ischaemia outcomes (for example, excludes haemorrhagic stroke), due to the requirement for comparing bleeding and ischaemia models for the purposes of assessing a bleeding/ischaemia trade-off. The definition should also include cardiovascular mortality, to match the BARC-5 fatal bleeding included in the bleeding outcome definition.

The best matching definition in Bosco et al. (2021)[@bosco2021major] (Table 1) is Ohm et al. (2018)[@ohm2018socioeconomic], because:

* It is simple (three-point), and includes only ischaemia outcomes (AMI, ischaemic stroke, and CV death)
* All codes used were fully defined;
* Codes used ICD-10 (instead of ICD-9).

The code groups are defined as follows:

??? note "AMI, ischaemic stroke, and CV death components of MACE used for ischaemia outcomes"

    | Category | ICD-10 | Description |
    |----------|--------|-------------|
    | AMI | I21.* | Acute myocardial infarction |  
    ||I22.*  | Subsequent myocardial infarction |
    |Ischaemic stroke|I63.* | Cerebral infarction |
    |CV death |I46.1 | Sudden cardiac death, so described |
    ||I46.9| Cardiac arrest, unspecified |

Disadvantages of this code group includes the lack of definition in whether the primary/secondary positions are used, and lack of validation. Similarly to the bleeding groups, basic validation may be performed by a chart analysis.

## Predictors

Clinical codes are used to define predictors, but an exclusion period of one month is applied to avoid using ICD-10 and OPCS-4 codes that would not have been coded yet before the index (clinical coding happens monthly, and clinical codes are not available until this processing has occurred). 

Depending on which data sources are used, other predictors may be available. For example, predictors in some models including primary care attribute flags, and physiological measurements such as HbA1c and blood pressure.

## Models

Classification models are trained on the bleeding and ischaemia outcomes within one year, which are binary (either an adverse event occurred or it did not). 

Both adverse outcomes have a low prevalence (0 - 20%). If individual patient risk is broadly localised at low values around the prevalence, it is not possible for any classification model to predict who will have adverse outcomes. Evidence for more determinstic outcomes, where a low number of patients have nearly 100% chance of adverse events and others have nearly 0% risk, would be provided by models that are able to predict adverse outcomes very well (i.e. with very high true negative/positive rates, and a very high ROC AUC).

Since very high ROC AUCs are not observed, the former interpretation of risk distribution is more likely. In this case, the adverse outcome is considered a proxy for high risk or low risk (instead of outcome occurred or outcome did not occur), and the result may be used in two possible ways:

* The classification outcome itself may be utilised directly as an estimate of whether the patient is high or low risk.
* The continuous parameter underlying the classification model decision may be used as an estimate of continuous patient risk (i.e. between 0% and 100%).

To test the accuracy of the model under the first interpretation, it is necessary to establish that patients estimated at high risk typically have more adverse events. In the second interpretation, estimates must be made of patients' true continuous risk, which requires an aggregate over patients in the testing set. This is discussed in the next section.

## Model Testing

Models are assessed according to two criteria:

* **Accuracy**: Whether the model produces the correct risk classifications or estimates;
* **Stability**: Whether the model produces consistent risk classifications or estimates.

Both these metrics are assessed by applying the models to data in the testing set, which is not used in the model fitting process. Accuracy is assessed through calibration plots, by grouping patients into similar-risk groups and comparing the prevalence in each group to the estimated risk.

Stability is assessed by training multiple models on bootstrap resamples of the training set, and comparing the model outputs for each patient.

## Minimum Performance Criteria

A minimum performance criteria for the models can be established by estimating the number of patients either positively or negatively affected by a change in intervention based on model risk estimates for bleeding and ischaemia.

The simplest model to perform these calculations is hosted [here](https://hbrtradeoff.streamlit.app). It assumes determinstic outcomes, meaning that all patients are assumed to be either 0% or 100% risk before an intervention is applied. More complex versions of the calculation could assume a more realistic distribution of patient risk, and/or allow for differences in the effect of the intervention depending on the real patient risk.

The model can be used to understand possible benefit or harm caused by taking action based on the estimates from bleeding/ischaemia models, based on the background prevalence of the outcomes, the performance of the model, and the modifications in risk caused by the intervention.

## Limitations of Administrative Data

While use of ICD-10 and OPCS-4 coded patient data is useful because of its size and availability, there are caveats regarding its use for models intended directly for patient care.

Coding is performed manually for financial purposes. There is evidence that internal inconsistencies in the data exist[@hardy2022data], that may impact tools designed for direct patient care. This modification of the intended purpose of the dataset should be considered if the data is to be used in clinical decision support tools.

There is a wide degree of choice involved in selecting code groups to define index events and outcomes[@bosco2022major], both of which directly determine what question a given model is addressing (rather than how accurate it is). It is not possible to assess how well the coding maps to clinical reality using any model metric; the only available method is chart review, which is not possible to perform directly using only HES data.

In addition to variability in choice of code groups, variability also exists regarding which episode (or epsiodes) of a spell is used to define an event, and which primary/secondary positions should be utilised. There is no systematic consensus on how these choices should be made when creating model for patient-care purposes.

Finally, it is hard to assess coding accuracy by comparing the prevalence of events with trial or study data, because trials and studies often introduce some bias due to the recruitment criteria causing a discrepancy compared to counts of events in the entire patient population.
