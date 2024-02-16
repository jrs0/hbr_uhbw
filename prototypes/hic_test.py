"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine, get_data
from pyhbr.middle import from_hic

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

#codes = from_hic.get_clinical_codes(engine, "icd10_arc_hbr.yaml", "opcs4_arc_hbr.yaml")
#lab_results = from_hic.get_lab_results(engine)

prescriptions = from_hic.get_prescriptions(engine)

# demographics = get_data(engine, hic.demographics_query)
# episodes = get_data(engine, hic.episodes_query, start_date, end_date)


# pharmacy_prescribing = get_data(engine, hic.pharmacy_prescribing_query)


# #patients = episodes[["patient_id"]].drop_duplicates()