import pyhbr.clinical_codes as codes

res = codes.load_from_package("icd10_blank.yaml")

x = res.codes_in_group("acs_bezin")