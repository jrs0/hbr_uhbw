import pyhbr.clinical_codes as codes
from serde.yaml import to_yaml

res = codes.load_from_package("icd10.yaml")

#f = codes.Index(index=("hello","bye"))

#print(to_yaml(f))