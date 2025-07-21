import logging
import knime.extension as knext
from sim_ext import main_category
from utils import parameter_utils as parameters
import pandas as pd
import json

# setup logger
LOGGER = logging.getLogger(__name__)

@knext.parameter_group(label="String Values")
class StringFactorValues:
    string_value = knext.StringParameter(
        "String Value",
        "Define a single categorical label to be used as a factor level (e.g., 'Low', 'Medium', 'High')"
    )
    
# define the KNIME node
@knext.node(
    name="Factor Definition (DoE)",
    node_type=knext.NodeType.OTHER,
    icon_path="icons/factor definition.png",
    category=main_category
)

@knext.input_table(
    name="Input Data", 
    description="A table containing metadata to define experimental factors"
)

@knext.output_table(
    name="Output Data", 
    description="A table where each column is a factor and rows represent all value combinations for the experiment design"
)

class FactorDefinitionDOE:
    """Generate factor definitions and value ranges for use in Design of Experiments (DoE)

        This node enables the definition of factor levels for simulation experiments.
        Based on either table-based metadata or manual input (argument-based), the node
        generates a KNIME table representing possible values for each factor, which can
        later be used to create experiment configurations.
    """

    factor_input_type = knext.EnumParameter(
        label="Input Type",
        description="Select how metadata is provided: as a 'normal' data table or as arguments",
        default_value=parameters.FactorInputType.TABLEBASED.name,
        enum=parameters.FactorInputType,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    )

    # string parameter to define the name of the output table
    # default value is set to "your_table"
    table_name = knext.StringParameter(
        "Table",
        "Enter the name of the table to use as a prefix for factor identifiers",
        default_value="your_table"
    ).rule(
        knext.OneOf(factor_input_type, [parameters.FactorInputType.TABLEBASED.name]),  
        knext.Effect.SHOW
    )
    
    # column parameter to select a unique identifier for each factor
    # only string-type columns from the first input table (port_index=0) are selectable
    unique_identifier = knext.ColumnParameter(
        "Identifier Column",
        "Select the column containing a unique identifier for each factor",
        port_index=0,
        column_filter=lambda c: c.ktype == knext.string()
    ).rule(
        knext.OneOf(factor_input_type, [parameters.FactorInputType.TABLEBASED.name]),  
        knext.Effect.SHOW
    )

    # column parameter to select the column containing factor names
    # only string-type columns are allowed, coming from the first input port
    factor_name = knext.ColumnParameter(
        "Name Column",
        "Select the column that contains the name or type of the factor",
        port_index=0,
        column_filter=lambda c: c.ktype == knext.string()
    ).rule(
        knext.OneOf(factor_input_type, [parameters.FactorInputType.TABLEBASED.name]),  
        knext.Effect.SHOW
    )

    # define a parameter to allow the user to select the expected data type of the factor column
    # the available types are defined in the FactorDataType enum (STRING, NUMERIC)
    # the UI uses a value switch to toggle between types
    factor_data_type = knext.EnumParameter(
        label="Data Type",
        description="Specify whether the factor values are categorical (String) or numeric (Numeric)",
        default_value=parameters.FactorDataType.STRING.name,
        enum=parameters.FactorDataType,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    )

    # column parameter for STRING data type
    # this parameter appears only if the user selects "STRING" as the data type
    # it allows selecting a column from the first input port (port_index=0),
    # only shown when the selected data type is STRING
    string_factor_value = knext.ColumnParameter(
        "Value Column",
        "Select the column that contains the string-based factor values",
        port_index=0,
        column_filter=lambda c: c.ktype == knext.string()
    ).rule(
        knext.OneOf(factor_data_type, [parameters.FactorDataType.STRING.name]),  
        knext.Effect.SHOW
    )

    # parameter array to configure multiple string values for a STRING-type factor
    # each item in the array is defined by the StringFactorValues() parameter group
    # displayed vertically in the UI with a button to add new entries
    # only shown when the selected data type is STRING
    string_configuration = knext.ParameterArray(
        label="String Values",
        description="Define the list of categorical values (levels) to be used for this string factor",
        parameters=StringFactorValues(),
        layout_direction=knext.LayoutDirection.VERTICAL,
        button_text="Add New String Value",
        array_title="String Value"
    ).rule(
        knext.OneOf(factor_data_type, [parameters.FactorDataType.STRING.name]),  
        knext.Effect.SHOW
    )

    # column parameter for NUMERIC data type
    # this parameter appears only if the user selects "NUMERIC" as the data type
    # it allows selecting a column from the first input port, but excludes string columns
    # only shown when the selected data type is NUMERIC
    numeric_factor_value = knext.ColumnParameter(
        "Value Column",
        "Select the column that contains the numeric factor values",
        port_index=0,
        column_filter=lambda c: c.ktype != knext.string()
    ).rule(
        knext.OneOf(factor_data_type, [parameters.FactorDataType.NUMERIC.name]),  
        knext.Effect.SHOW
    )

    # integer parameter to define the minimum value for numeric factors
    # only shown when the selected data type is NUMERIC
    min_value = knext.IntParameter(
        "Minimum",
        "Define the minimum numeric value to be included for this factor",
        default_value=0
    ).rule(
        knext.OneOf(factor_data_type, [parameters.FactorDataType.NUMERIC.name]),
        knext.Effect.SHOW
    )

    # integer parameter to define the maximum value for numeric factors
    # only shown when the selected data type is NUMERIC
    max_value = knext.IntParameter(
        "Maximum",
        "Define the maximum numeric value to be included for this factor",
        default_value=1
    ).rule(
        knext.OneOf(factor_data_type, [parameters.FactorDataType.NUMERIC.name]),
        knext.Effect.SHOW
    )

    # integer parameter to define the step size between values for numeric factors
    # only shown when the selected data type is NUMERIC
    step_value = knext.IntParameter(
        "Step",
        "Define the increment between values from minimum to maximum (inclusive)",
        default_value=1
    ).rule(
        knext.OneOf(factor_data_type, [parameters.FactorDataType.NUMERIC.name]),
        knext.Effect.SHOW
    )

    def configure(self, configure_context, input_schema_1):
        configure_context.set_warning("This is a warning during configuration")

    def execute(self, exec_context, input_1):
        from utils import factor_utils

        # initialize the dictionary that will hold factor names as keys and their value ranges as lists
        factor_dict = {}

        # handle the case where factor definitions are provided via input table metadata
        if self.factor_input_type == parameters.FactorInputType.TABLEBASED.name:
            # convert the input KNIME table to a pandas DataFrame
            input_df = input_1.to_pandas()

            # retrieve user-defined metadata to construct factor identifiers
            tab_name = self.table_name
            unique_col = self.unique_identifier
            name_col = self.factor_name

            # select the appropriate value column depending on the factor's data type
            value_col = (
                self.string_factor_value
                if self.factor_data_type == parameters.FactorDataType.STRING.name
                else self.numeric_factor_value
            )

            # retrieve the value list and its range boundaries using utility function
            values, min_val, max_val, step_val = factor_utils.get_values(self, exec_context, value_col)

            # extract all unique (identifier, factor name) pairs to define individual factors
            # ensure each factor is processed only once → exclude rows with missing identifiers or names → convert to NumPy array for iteration
            combinations = (
                input_df[[unique_col, name_col]]
                .drop_duplicates()  
                .dropna()           
                .values             
            )

            # generate a unique factor key for each combination and assign a value range to it
            for unique_val, name_val in combinations:
                factor_key = (
                    f"{tab_name}"
                    f":[{unique_col}]{unique_val}"
                    f":[{name_col}]{name_val}"
                    f":{value_col}"
                )

                # assign the generated range to the factor key
                factor_dict[factor_key] = list(range(min_val, max_val + 1, step_val))

            # convert the dictionary to a DataFrame (wide format: one column per factor)
            df = pd.DataFrame(factor_dict)

        # handle the case where the factor is defined manually via node arguments
        elif self.factor_input_type == parameters.FactorInputType.ARGUMENTBASED.name:
            value_col = (
                self.string_factor_value
                if self.factor_data_type == parameters.FactorDataType.STRING.name
                else self.numeric_factor_value
            )

            # retrieve just the list of values for this standalone factor
            values, _, _, _ = factor_utils.get_values(self, exec_context, value_col)

            # build a single-column DataFrame for the defined values
            df = pd.DataFrame({value_col: values})

        # convert the pandas DataFrame back into a KNIME table and return it as output
        return knext.Table.from_pandas(df)


# Gedanke #2: NUMERIC-Value Eingabe nochmal überdenken, falls es "definierte" Level gibt
# hier dann ggf. auch eher ParameterArray → auf jeden Fall aus DoE-Node nochmal ansehen und ggf. anpassen

# Gedanke #3: User-First, auch mit Falk und Co. ansehen und diskutieren