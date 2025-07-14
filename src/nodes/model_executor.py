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

@knext.input_table(name="Test", description="...")
@knext.output_table(name="Output Data", description="Result of simulation model setup.")

class ModelExecutor:
    """Short one-line description of the node.
        ...
    """
    executable_path = knext.LocalPathParameter(
        label="Executable Path", 
        description="Enter a path to the executable model file. The required syntax of the path depends on the chosen file system",
        placeholder_text="my/path/[model.bat/.sh/...]"
    )

    #test = knext.StringParameter(
    #    label="test",
    #    description="...",
    #    choices=knext.DialogCreationContext.get_flow_variables()
    #)

    flow_variable_param = knext.StringParameter(
        label="Flow variable param",
        description="Call it a choice",
        choices=lambda a: knext.DialogCreationContext.get_flow_variables(a),
    )

    

    # todo

    # Configuration-time logic
    def configure(self, configure_context, input_schema_1):
        configure_context.set_warning("This is a warning during configuration")

    # Main execution logic
    def execute(self, exec_context, input_1):
        
        if platform.system() == "Windows":
            exec_context.flow_variables["os_slash"] = "\\"
        else:
            exec_context.flow_variables["os_slash"] = "/"

        return