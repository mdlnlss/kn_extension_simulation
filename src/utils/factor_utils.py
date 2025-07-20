import logging
import knime_extension as knext
from utils import parameter_utils as parameters
import json
import pandas as pd

# setup logger
LOGGER = logging.getLogger(__name__)

# creates a numeric representation for a list of string values
def factor_string_mapping(string_values):
    """
        generates a numeric representation for a list of string values

        returns:
            - a list of numeric indices (e.g., [0, 1, 2, ...])
            - a dictionary mapping those indices (as strings) back to the original string values
            (e.g., {"0": "Low", "1": "Medium", "2": "High"})

        this is useful for encoding categorical factor levels as numeric values during experiment generation
    """

    return list(range(len(string_values))), {str(i): val for i, val in enumerate(string_values)}

# generates the set of possible values for a factor column based on its data type (string or numeric)
def get_values(node, exec_context, column_name):
    """
        determines the set of values for a factor based on its data type

        if the factor is of type STRING:
            - extracts string values from the node’s configuration
            - creates a numeric encoding and corresponding mapping dictionary
            - stores the mapping in flow variables for later reference
            - returns: (list of numeric values, min, max, step) → (e.g., [0, 1, 2], 0, 2, 1)

        if the factor is of type NUMERIC:
            - uses min, max, and step values from the node configuration to generate a range
            - returns: (list of values, min, max, step) → (e.g., [0, 5, 10], 0, 10, 5)

        parameters:
            node: an instance with factor configuration attributes (data type, string values, min/max/step)
            exec_context: execution context containing flow_variables to store mappings
            column_name: name of the value column to associate with the mapping

        returns:
            tuple: (list of numeric values, min_value, max_value, step_value)
    """

    if node.factor_data_type == parameters.FactorDataType.STRING.name:
        # extract string values from the node’s parameter array
        strings = [cfg.string_value for cfg in node.string_configuration]

        # convert to numeric range and create a mapping dictionary
        values, mapping = factor_string_mapping(strings)

        # store the mapping as a flow variable so it can be used later for labeling or reverse mapping
        exec_context.flow_variables[f"factor-mapping_{column_name}"] = json.dumps(mapping)

        # return the numeric values and range boundaries for downstream processing
        return values, 0, len(strings) - 1, 1

    else:
        # for numeric types, return the value range based on user-defined min, max, and step
        return list(range(node.min_value, node.max_value + 1, node.step_value)), node.min_value, node.max_value, node.step_value

def doe_string_mapping(df: pd.DataFrame, flow_vars: dict, axis: int = 0) -> pd.DataFrame:
    """
        applies string label mappings to a DoE (Design of Experiments) DataFrame using flow variables

        string-based mappings are used to convert numeric-coded factor values (e.g., 0, 1, 2)
        back into their original string labels (e.g., 'Low', 'Medium', 'High'), based on
        flow variables created during factor setup (usually from STRING-type factor definitions)

        parameters:
            df (pd.DataFrame): the DataFrame to apply the mappings to
                - if axis=0: expects wide format (factors are columns)
                - if axis=1: expects long format (factors and values are in rows)
            flow_vars (dict): dictionary of KNIME flow variables containing mapping JSON
                - keys must be of the form 'factor-mapping_<column_name>'
            axis (int): controls format interpretation
                - 0: wide format (column-wise mapping)
                - 1: long format (row-wise mapping based on COL_VALUE)

        returns:
            pd.DataFrame: a DataFrame where applicable values are mapped from numeric indices
            to their original string labels using the provided mappings
    """

    # dictionary to hold column-to-mapping-dictionary associations
    mappings = {}  

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