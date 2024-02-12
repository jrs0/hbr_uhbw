"""Simple testing script for HIC data processing
"""

import datetime as dt

from pyhbr.common import make_engine, get_data
from pyhbr.data_source import hic

start_date = dt.date(1990, 1, 1)
end_date = dt.date(2030, 1, 1)

engine = make_engine()

demographics = get_data(engine, hic.demographics_query)
episodes = get_data(engine, hic.episodes_query, start_date, end_date)
diagnoses = get_data(engine, hic.diagnoses_query)
procedures = get_data(engine, hic.procedures_query)
pathology_blood = get_data(
    engine, hic.pathology_blood_query, ["OBR_BLS_UE", "OBR_BLE_FB"]
)
pharmacy_prescribing = get_data(engine, hic.pharmacy_prescribing_query)


#patients = episodes[["patient_id"]].drop_duplicates()