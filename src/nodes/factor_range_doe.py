import logging
import knime.extension as knext
import pandas as pd
from doepy import build
import time

# Setup logger
LOGGER = logging.getLogger(__name__)

# COMMENT
#class Granularity(knext.EnumParameterOptions):
#    TABLE = ("Complete Table", "...")
#    VALUE = ("Specific Values", "...")

@knext.parameter_group(label="Dynamic Selection")
class FactorConfiguration:
    table_name = knext.StringParameter(
        "Table",
        "...",
        default_value="your_table"
    )
    
    unique_identifier = knext.ColumnParameter(
        "Identifier",
        "Select the column with your factor's unique identifier",
        port_index=0
    )

    factor_name = knext.ColumnParameter(
        "Name",
        "Select the column with the factor name",
        port_index=0
    )

    factor_value = knext.ColumnParameter(
        "Value",
        "Select the column with the factor values",
        port_index=0
    )

    min_value = knext.IntParameter(
        "Minimum",
        "...",
        default_value=0
    )

    max_value = knext.IntParameter(
        "Maximum",
        "...",
        default_value=1
    )

    step_value = knext.IntParameter(
        "Step",
        "...",
        default_value=1
    )

# Define the KNIME node
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

    # Factor Configuration
    factor_configuration = knext.ParameterArray(
        label="Factor Configuration",
        description="...",
        parameters=FactorConfiguration(),
        layout_direction=knext.LayoutDirection.HORIZONTAL,
        button_text="Add New Configuration",
        array_title="Factor Configuration",
    )

    # COMMENT
    #doe_mode = knext.EnumParameter(
    #    label="Mode",
    #    description="...",
    #    default_value=Granularity.TABLE.name,
    #    enum=Granularity,
    #    style=knext.EnumParameter.Style.VALUE_SWITCH,
    #)


    # Configuration-time logic
    def configure(self, configure_context, input_schema_1):
        configure_context.set_warning("This is a warning during configuration")

        for config in self.factor_configuration:
            value_col_name = config.factor_value
            value_col_spec = input_schema_1[value_col_name]
            value_type = value_col_spec.type
            configure_context.set_warning("Spaltentyp: " + value_type)


            #is_numeric = value_type in (knext.

            #configure_context.set_visible(config, "min_value", is_numeric)
            #configure_context.set_visible(config, "max_value", is_numeric)
            #configure_context.set_visible(config, "step_value", is_numeric)

        configure_context.set_warning("Configuration updated based on column type.")

    # Main execution logic
    def execute(self, exec_context, input_1):

        input_df = input_1.to_pandas()
        factor_dict = {}

        # Iterate trough factor_configuration
        for i, config in enumerate(self.factor_configuration):
            tab_name = config.table_name
            unique_col = config.unique_identifier
            name_col = config.factor_name
            value_col = config.factor_value

            name = f"{tab_name}%{unique_col}/{name_col}:{value_col}"

            min_val = config.min_value
            max_val = config.max_value
            step_val = config.step_value

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