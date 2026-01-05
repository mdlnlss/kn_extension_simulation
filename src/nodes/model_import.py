import logging
import knime.extension as knext
from utils import parameter_utils as pdef, port
from sim_ext import main_category
from typing import TextIO, BinaryIO
import pandas as pd


# setup logger
LOGGER = logging.getLogger(__name__)
    
# define the KNIME node
@knext.node(
    name="Simulation Model Importer",
    node_type=knext.NodeType.SOURCE,
    icon_path="icons/simulation_import.png",
    category=main_category
)

@knext.output_port(name="Output Data", description="Result of simulation model setup.", port_type=port.simulation_port_type)
@knext.output_table(name="SimPy Arguments", description="...")

class ModelImporterCustom:
    """Short one-line description of the node.
        This node enables structured integration of external simulation models into a KNIME workflow.
        It supports multiple simulation tools and abstracts the differences in model file structures and configuration options.

        ### Supported Tools:
        - **AnyLogic**: Import a `.jar`-based model with either database or file-based input.
        - **AutoSched AP**: Import a `.xmdx` model file including its associated model name.
        - **SimPy**: Import a `.py` simulation script with an optional output file path.

        ### Features:
        - Dynamically adapts visible settings based on the selected simulation tool.
        - Validates required paths and file types during configuration and execution.
        - Automatically prepares a standardized `Resources/` directory within the KNIME workspace.
        - Makes selected configuration values available as flow variables (e.g., DB host, port, dialect, etc.).
        - Provides tool-specific information in the node output.

        ### Output Table:
        The output is a single-row table containing key metadata about the imported model,
        including paths, tool type, and configuration details relevant to the selected tool.
    """

    # tool selection
    tool_choice = knext.EnumParameter(
        label="Simulation Tool",
        description="Select the simulation tool you are using.",
        default_value=pdef.SimTools.ANYLOGIC.name,
        enum=pdef.SimTools,
        style=knext.EnumParameter.Style.DROPDOWN,
    )

    # AnyLogic model path input
    anylogic_model_path = knext.LocalPathParameter(
        label="Model Path", 
        description="Enter a path to the model (.jar).",
        placeholder_text="my/path/model.jar"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.ANYLOGIC.name]), knext.Effect.SHOW)

    # validation for AnyLogic model path
    @anylogic_model_path.validator
    def validate_al_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith(".jar"):
            raise ValueError("Invalid path: must end with '.jar'")

    # ASAP tool model path
    asap_model_path = knext.LocalPathParameter(
        label="Model Path", 
        description="Enter a path to the model .xmdx file. The required syntax of the path depends on the chosen file system",
        placeholder_text="my/path/model.xmdx"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.ASAP.name]),  knext.Effect.SHOW)

    # validation for ASAP model path
    @asap_model_path.validator
    def validate_asap_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith(".xmdx"):
            raise ValueError ("Invalid path: must end with '.xmdx'")

    # ASAP model name
    asap_model_name = knext.StringParameter(
        label="Model",
        description="Model name",
        default_value="your_model"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.ASAP.name]),  knext.Effect.SHOW)
        
    # SimPy model path
    simpy_model_path = knext.LocalPathParameter(
        label="Model Path", 
        description="Enter a path to the XXX. The required syntax of the path depends on the chosen file system",
        placeholder_text="my/path/model.py"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.SIMPY.name]),  knext.Effect.SHOW)


    # validation for SimPy model path
    @simpy_model_path.validator
    def validate_simpy_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith(".py"):
            raise ValueError ("Invalid path: must end with '.py'")

    # output type
    simulation_output = knext.EnumParameter(
        label="Output Type",
        description="...",
        default_value=pdef.SimulationOutputType.FILEBASED.name,
        enum=pdef.SimulationOutputType,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    )

    # output file name / before: simpy_output
    output_file = knext.StringParameter(
        label="Output Filename",
        description="Name of the file to be generated (e.g. results.csv).",
        default_value="output.csv"
    ).rule(knext.OneOf(simulation_output, [pdef.SimulationOutputType.FILEBASED.name]), knext.Effect.SHOW)
    
    # configuration-time logic
    def configure(self, configure_context):
        configure_context.set_warning("This is a warning during configuration")

    # main execution logic
    def execute(self, exec_context):
        import os
        import shutil
        import subprocess
        import re
        import json
        import sys
        import pandas as pd

        # path Mapping
        tool_paths = {
            pdef.SimTools.ANYLOGIC.name: self.anylogic_model_path,
            pdef.SimTools.ASAP.name: self.asap_model_path,
            pdef.SimTools.SIMPY.name: self.simpy_model_path
        }
        
        selected_path = tool_paths.get(self.tool_choice, "")

        if not selected_path or not os.path.isfile(selected_path):
            raise FileNotFoundError(f"Model file not found: {selected_path}")

        # workspace navigation
        workflow_data_dir = exec_context.get_workflow_data_area_dir()
        workspace_folder_dir = os.path.abspath(os.path.join(workflow_data_dir, "..", ".."))
        created_folder_dir = os.path.join(workspace_folder_dir, "Resources")

        exec_context.flow_variables.update({
            "simulation_tool": self.tool_choice,
            "output_mode": self.simulation_output,
            "workflow_folder_dir": workspace_folder_dir,
            "resource_folder": created_folder_dir
        })

        # safe resource preparation
        os.makedirs(created_folder_dir, exist_ok=True)

        # copy model files
        model_dir = os.path.dirname(selected_path)
        try:
            # dirs_exist_ok=True allows copying into an existing directory and overwriting files
            shutil.copytree(model_dir, created_folder_dir, dirs_exist_ok=True)
            LOGGER.info(f"Updated resources in {created_folder_dir}")
        except Exception as e:
            LOGGER.warning(f"Could not overwrite some files in {created_folder_dir}: {e}")
            # continue anyway; if the model file itself is updated, the simulation should work

        model_path_in_res = os.path.join(created_folder_dir, os.path.basename(selected_path))
        exec_context.flow_variables["model_path"] = model_path_in_res

        # tool-specific logic
        argument_defaults = {}

        if self.tool_choice == pdef.SimTools.ANYLOGIC.name:
            if self.simulation_output == pdef.SimulationOutputType.FILEBASED.name:
                exec_context.flow_variables["output_file"] = self.output_file

        elif self.tool_choice == pdef.SimTools.SIMPY.name:
            try:
                result = subprocess.run(
                    [sys.executable, model_path_in_res, "--help"],
                    capture_output=True, text=True, check=True
                )
                help_output = result.stdout or result.stderr
                
                # parsing logic
                clean_output = " ".join(help_output.splitlines())
                pattern = r"--([\w\-]+).*?\(default:\s*([^)]+)\)"
                matches = re.findall(pattern, clean_output)
                argument_defaults = {k: [v.strip()] for k, v in matches}

                exec_context.flow_variables["simpy_help_output"] = json.dumps(argument_defaults)
                
                if self.simulation_output == pdef.SimulationOutputType.FILEBASED.name:
                    exec_context.flow_variables["output_file"] = f"--output {self.output_file}"
                    
            except subprocess.CalledProcessError as e:
                LOGGER.error(f"SimPy help execution failed: {e.stderr}")
                raise

        # return values
        if self.tool_choice == pdef.SimTools.SIMPY.name and argument_defaults:
            df_meta = pd.DataFrame.from_dict(argument_defaults)
            df_meta = df_meta.apply(pd.to_numeric, errors='ignore')
            return port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res), knext.Table.from_pandas(df_meta)
        
        return port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res), knext.Table.from_pandas(pd.DataFrame())