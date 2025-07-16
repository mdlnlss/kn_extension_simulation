import json
import logging
import pandas as pd

LOGGER = logging.getLogger(__name__)

def apply_factor_mappings(df: pd.DataFrame, flow_vars: dict, axis: int = 0) -> pd.DataFrame:
    """
    todo: description
    """

    mappings = {}
    for key, val in flow_vars.items():
        if key.startswith("factor-mapping_"):
            col = key.replace("factor-mapping_", "")
            try:
                mappings[col] = json.loads(val)
            except Exception as e:
                LOGGER.warning(f"Mapping aus Flow-Variable '{key}' konnte nicht geladen werden: {e}")

    if axis == 0:
        for col in df.columns:
            if col == "CONFIGURATION":
                continue
            value_col = col.split(":")[-1]
            mapping = mappings.get(value_col)
            if mapping:
                df[col] = df[col].apply(lambda v: mapping.get(str(int(round(float(v)))), v) if pd.notna(v) else v)
    elif axis == 1:

        def replace_value(row):
            col_key = row.get("COL_VALUE")
            mapping = mappings.get(col_key)
            if mapping:
                try:
                    v_rounded = str(int(round(float(row["VALUES"]))))
                    return mapping.get(v_rounded, row["VALUES"])
                except:
                    return row["VALUES"]
            return row["VALUES"]

        df["VALUES"] = df.apply(replace_value, axis=1)

    return df
