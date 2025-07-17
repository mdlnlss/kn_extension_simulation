import json
import logging
import pandas as pd

LOGGER = logging.getLogger(__name__)

def string_factor_mapping(df: pd.DataFrame, flow_vars: dict, axis: int = 0) -> pd.DataFrame:
    """
    applies string-based factor mappings from KNIME flow variables to a pandas DataFrame

    the flow variables are expected to contain JSON-encoded dictionaries under keys with the pattern
    'factor-mapping_<column_name>', where <column_name> corresponds to a value column in the data

    the mapping replaces numeric or encoded values with user-defined labels or names, based on the context:
    - axis = 0: operates on a wide-format DataFrame (columns = factors)
    - axis = 1: operates on a long-format DataFrame (row-wise values)

    parameters:
        df (pd.DataFrame): the DataFrame to apply the mappings to
        flow_vars (dict): KNIME flow variables passed from the execution context
        axis (int): if 0, apply mappings column-wise (wide format); if 1, apply row-wise (long format)

    returns:
        pd.DataFrame: the transformed DataFrame with mapped values where applicable
    """

    mappings = {}  # dictionary to hold column-to-mapping-dictionary associations

    # extract all flow variables that match the 'factor-mapping_' prefix
    for key, val in flow_vars.items():
        if key.startswith("factor-mapping_"):
            col = key.replace("factor-mapping_", "")
            try:
                # parse the JSON string into a Python dict
                mappings[col] = json.loads(val)
            except Exception as e:
                LOGGER.warning(f"Mapping from flow variable '{key}' could not be loaded: {e}")

    if axis == 0:
        # apply mappings to wide-format table (columns contain values to replace)
        for col in df.columns:
            if col == "CONFIGURATION":
                continue

            # extract the value column name from the full column label
            value_col = col.split(":")[-1]  
            mapping = mappings.get(value_col)

            if mapping:
                # apply mapping to each cell: convert to float → round → int → str → mapped label
                df[col] = df[col].apply(
                    lambda v: mapping.get(str(int(round(float(v)))), v) if pd.notna(v) else v
                )

    elif axis == 1:
        # apply mappings to long-format table (values are in a single column per row)
        def replace_value(row):
            col_key = row.get("COL_VALUE")
            mapping = mappings.get(col_key)

            if mapping:
                try:
                    # same conversion logic as above but applied per row
                    v_rounded = str(int(round(float(row["VALUES"]))))
                    return mapping.get(v_rounded, row["VALUES"])
                except:
                    return row["VALUES"]
            return row["VALUES"]

        # apply the mapping row-wise
        df["VALUES"] = df.apply(replace_value, axis=1)

    return df