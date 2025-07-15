import logging
import knime.extension as knext
import os
import platform
import pandas as pd
import shutil
from utils import knutils

# Setup logger
LOGGER = logging.getLogger(__name__)

# Define the KNIME node
@knext.node(
    name="Table Specs to DoE Input", # change! #Preparation for DoE?
    node_type=knext.NodeType.OTHER,
    icon_path="icons/icon.png",
    category="/community/simulation"
)

@knext.input_table(name="Test", description="...")
@knext.output_table(name="Output Data", description="...")

class SpecsToDOE:
    """Short one-line description of the node.
        ...
    """

    # Configuration-time logic
    def configure(self, configure_context, input_schema_1):

        schema = input_schema_1

        if not schema:
            configure_context.set_warning("Input has no columns.")

        configure_context.set_warning("This is a warning during configuration")

    # Main execution logic
    def execute(self, exec_context, input_1):
        
        df_origin = input_1.to_pandas()
        flow_vars = exec_context.flow_variables

        # Beispiel: {"table-selection": "toolgroups", ...}
        if "table-selection" in flow_vars:
            selection_value = flow_vars["table-selection"]
            new_var_name = f"table-selection_{selection_value}"
            columns_var_name = f"columns_{selection_value}"

            LOGGER.warning("Adding selection flow var: %s = %s", new_var_name, selection_value)

            # Neue Flow-Variable setzen
            exec_context.flow_variables[new_var_name] = selection_value

            columns_str = ",".join(df_origin.columns)
            exec_context.flow_variables[columns_var_name] = columns_str


        #LOGGER.warning("Verfügbare Flow-Variablen: %s", list(flow_vars.keys()))
        
        

        return knext.Table.from_pandas(df_origin)