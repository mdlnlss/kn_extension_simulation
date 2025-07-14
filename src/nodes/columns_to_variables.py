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
    name="Table Columns to Variables (String)", # change! #Preparation for DoE?
    node_type=knext.NodeType.OTHER,
    icon_path="icons/icon.png",
    category="/simulation"
)

@knext.input_table(name="Test", description="...")
@knext.output_table(name="Output Data", description="Result of simulation model setup.")

class ColumnsToVariables:
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

        df = df_origin.select_dtypes(include='string')

        if df.empty:
            raise knext.WorkflowExecutionError("Input table is empty.")

        for col in df.columns:
            values = df[col].dropna().astype(str).unique().tolist()
            joined = ",".join(values)
            exec_context.flow_variables[col] = joined
            LOGGER.info(f"Flow variable '{col}' set to '{joined}'")

        return knext.Table.from_pandas(df_origin)