# Bleeding/Ischaemia Risk Estimation Report

NOTE: ALTHOUGH THE GENERATED REPORT CONTAINS AGGREGATE
DATA/FIGURES ONLY, SOME DATA FILES IN THIS FOLDER CONTAIN
PATIENT-LEVEL DATA.

This folder contains the results of modelling the
risk of bleeding and ischaemia in heart attack patients
who have been prescribed DAPT.

The intention of this folder is to contain the source
code for the report, and all data files, images, tables
and figures in an easily accessible format that can be
adapted as necessary for other reports or publications.

## Compiling the report

The main report file is `report.qmd`, which is a Quarto
document. To compile the report, install Quarto
(see [here](https://quarto.org/docs/get-started/)),
open a terminal, and run:

```bash
quarto render report.qmd
```

The are multiple methods of compiling Quarto
documents, depending on your programming language
or platform. All of them should work, because
the report does not contain any embedded program 
snippets that need executing.

## Description of files

Files used in the report are stored in the folders
`images/`, `models/` and `tables/`. Most files have
the format `{name}_{commit}_{timestamp}.extension`.
The `name` identifies what the file is. The `commit`
contains a commit hash of the state of the
[hbr_uhbw](https://github.com/jrs0/hbr_uhbw) repository.
The `timestamp` contains the time at which the file was
save (which is normally close to the time at which the
data for the file was generated). You can use a tool
like [this one](https://www.unixtimestamp.com/) to 
convert the timestamp to a readable date/time.

The folders are used as follows:

* `models/` contains the raw model files, trained using
   scikit learn.
* `images/` contains figures generated from the model files,
   including ROC curves and calibration/stability plots.
* `tables/` contains tables used in the report, e.g. showing
   outcome prevalence in the dataset or comparing model 
   performance. 

The report file `report.qmd` loads files by path, making it
easy to see which figure or table file corresponds to which
plot in the report.

## References

The references used in the report are contained in `ref.bib`. 
There are many online tools for converting this into other
formats, e.g. [this one](https://asouqi.github.io/bibtex-converter/).

