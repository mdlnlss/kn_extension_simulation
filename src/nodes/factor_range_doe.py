import logging
import knime.extension as knext
import pandas as pd
from doepy import build
import time
import json

# setup logger
LOGGER = logging.getLogger(__name__)

class FactorDataType(knext.EnumParameterOptions):
    STRING = ("String", "...")
    NUMERIC = ("Numeric", "...")

@knext.parameter_group(label="String Values")
class StringFactorValues:
    string_value = knext.StringParameter(
        "String Value",
        "..."
    )
    
# define the KNIME node
@knext.node(
    name="Factor Range (DoE)",
    node_type=knext.NodeType.OTHER,
    icon_path="icons/try.png",
    category="/community/simulation"
)

@knext.input_table(name="Input Data", description="...")
@knext.output_table(name="Output Data", description="...")

class FactorRangeDOE:
    """Short one-line description of the node.
        This node enables ...
    """

    # string parameter to define the name of the output table
    # default value is set to "your_table"
    table_name = knext.StringParameter(
        "Table",
        "...",
        default_value="your_table"
    )
    
    # column parameter to select a unique identifier for each factor
    # only string-type columns from the first input table (port_index=0) are selectable
    unique_identifier = knext.ColumnParameter(
        "Identifier Column",
        "Select the column with your factor's unique identifier",
        port_index=0,
        column_filter=lambda c: c.ktype == knext.string()
    )

    # column parameter to select the column containing factor names
    # only string-type columns are allowed, coming from the first input port
    factor_name = knext.ColumnParameter(
        "Name Column",
        "Select the column with the factor name",
        port_index=0,
        column_filter=lambda c: c.ktype == knext.string()
    )

    # define a parameter to allow the user to select the expected data type of the factor column
    # the available types are defined in the FactorDataType enum (STRING, NUMERIC)
    # the UI uses a value switch to toggle between types
    factor_data_type = knext.EnumParameter(
        label="Data Type",
        description="...",
        default_value=FactorDataType.STRING.name,
        enum=FactorDataType,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    )

    # column parameter for STRING data type
    # this parameter appears only if the user selects "STRING" as the data type
    # it allows selecting a column from the first input port (port_index=0),
    # and only shows columns with a string data type (e.g., categorical variables)
    string_factor_value = knext.ColumnParameter(
        "Value Column",
        "Select the column with the factor values",
        port_index=0,
        column_filter=lambda c: c.ktype == knext.string()
    ).rule(
        knext.OneOf(factor_data_type, [FactorDataType.STRING.name]),  
        knext.Effect.SHOW
    )

    # parameter array to configure multiple string values for a STRING-type factor
    # each item in the array is defined by the StringFactorValues() parameter group
    # displayed vertically in the UI with a button to add new entries
    # only shown when the selected data type is STRING
    string_configuration = knext.ParameterArray(
        label="String Values",
        description="...",
        parameters=StringFactorValues(),
        layout_direction=knext.LayoutDirection.VERTICAL,
        button_text="Add New String Value",
        array_title="String Value"
    ).rule(
        knext.OneOf(factor_data_type, [FactorDataType.STRING.name]),  
        knext.Effect.SHOW
    )

    # column parameter for NUMERIC data type
    # this parameter appears only if the user selects "NUMERIC" as the data type
    # it allows selecting a column from the first input port, but excludes string columns
    # useful for numeric factors such as time value or quantities 
    numeric_factor_value = knext.ColumnParameter(
        "Value Column",
        "Select the column with the factor values",
        port_index=0,
        column_filter=lambda c: c.ktype != knext.string()
    ).rule(
        knext.OneOf(factor_data_type, [FactorDataType.NUMERIC.name]),  
        knext.Effect.SHOW
    )

    # integer parameter to define the minimum value for numeric factors
    # only shown when the selected data type is NUMERIC
    min_value = knext.IntParameter(
        "Minimum",
        "...",
        default_value=0
    ).rule(
        knext.OneOf(factor_data_type, [FactorDataType.NUMERIC.name]),
        knext.Effect.SHOW
    )

    # integer parameter to define the maximum value for numeric factors
    # only shown when the selected data type is NUMERIC
    max_value = knext.IntParameter(
        "Maximum",
        "...",
        default_value=1
    ).rule(
        knext.OneOf(factor_data_type, [FactorDataType.NUMERIC.name]),
        knext.Effect.SHOW
    )

    # integer parameter to define the step size between values for numeric factors
    # only shown when the selected data type is NUMERIC
    step_value = knext.IntParameter(
        "Step",
        "...",
        default_value=1
    ).rule(
        knext.OneOf(factor_data_type, [FactorDataType.NUMERIC.name]),
        knext.Effect.SHOW
    )


    # configuration-time logic
    def configure(self, configure_context, input_schema_1):
        configure_context.set_warning("This is a warning during configuration")

    # main execution logic
    def execute(self, exec_context, input_1):

        input_df = input_1.to_pandas()
        factor_dict = {}

        tab_name = self.table_name
        unique_col = self.unique_identifier
        name_col = self.factor_name

        value_col = ""
        min_val = 0
        max_val = 0
        step_val = 0

        if self.factor_data_type == FactorDataType.STRING.name:
            value_col = self.string_factor_value

            string_val = [cfg.string_value for cfg in self.string_configuration]
            map_strings_to_numeric = {str(i): val for i, val in enumerate(string_val)}

            exec_context.flow_variables[f"factor-mapping_{value_col}"] = json.dumps(map_strings_to_numeric)

            min_val = 0
            max_val = len(string_val) - 1
            step_val = 1

        elif self.factor_data_type == FactorDataType.NUMERIC.name:
            value_col = self.numeric_factor_value
            min_val = self.min_value
            max_val = self.max_value
            step_val = self.step_value

        combinations = (
            input_df[[unique_col, name_col]]
            .drop_duplicates()
            .dropna()
            .values
        )

        for unique_val, name_val in combinations:
            factor_name = (
                f"{tab_name}"
                f":[{unique_col}]{unique_val}"
                f":[{name_col}]{name_val}"
                f":{value_col}"
            )
            values = list(range(min_val, max_val + 1, step_val))
            factor_dict[factor_name] = values

        df = pd.DataFrame(factor_dict)

        return knext.Table.from_pandas(df)