from pyhbr.common import save_item, load_item
import pandas as pd

df = pd.DataFrame({"a": [1,2,3], "b": [4,5,6]})
save_item(df, "test_data")

df2 = load_item("test_data", True)