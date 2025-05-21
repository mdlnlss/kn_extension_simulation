import logging
import knime.extension as knext
import os
import platform
import pandas as pd
import shutil

# Setup logger
LOGGER = logging.getLogger(__name__)

# Define the KNIME node
@knext.node(
    name="Simulation Model Executor",
    node_type=knext.NodeType.SINK,
    icon_path="icons/model.png",
    category="/simulation"
)

@knext.output_table(name="Output Data", description="Result of simulation model setup.")

class ModelExecutor:
    """Short one-line description of the node.
        ...
    """

    # todo

    # Configuration-time logic
    def configure(self, configure_context):
        configure_context.set_warning("This is a warning during configuration")

    # Main execution logic
    def execute(self, exec_context):
        # todo

        return