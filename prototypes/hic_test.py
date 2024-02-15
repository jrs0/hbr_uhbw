"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine
from pyhbr.middle import from_hic

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

####
engine = make_engine()

codes = from_hic.get_clinical_codes(engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml")


####

# demographics = get_data(engine, hic.demographics_query)
# episodes = get_data(engine, hic.episodes_query, start_date, end_date)

# pathology_blood = get_data(
#     engine, hic.pathology_blood_query, ["OBR_BLS_UE", "OBR_BLE_FB"]
# )
# pharmacy_prescribing = get_data(engine, hic.pharmacy_prescribing_query)


# #patients = episodes[["patient_id"]].drop_duplicates()