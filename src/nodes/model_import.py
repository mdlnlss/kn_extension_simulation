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
@knext.output_table_group(name="SimPy Arguments", description="A table pre-filled with the default argument values parsed from the SimPy model's --help output. Only active when SimPy is selected as the simulation tool.")

class ModelImporterCustom:
    """Import a simulation model and prepare it for execution within a KNIME workflow.

        This node registers an external simulation model and copies its files into a
        structured resource directory inside the KNIME workspace. Configuration values
        are passed downstream as flow variables.

        ### Supported Tools:
        - **AnyLogic**: Import a `.jar`-based model with file-based or database output.
        - **SimPy**: Import a `.py` simulation script; arguments are parsed automatically.
        - **Other (CMD-based)**: Integrate any simulation tool executable via a custom command-line call.

        ### Features:
        - Adapts visible settings dynamically based on the selected simulation tool.
        - Validates model file paths and types at configuration time.
        - Creates a timestamped `Resources/` directory in the KNIME workspace.
        - Exports key settings (tool, model path, output mode, CMD command) as flow variables.

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
        description="Enter the path to the AnyLogic model export (.jar). The file must exist on the local file system.",
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

    # Other (CMD-based) tool model path
    other_model_path = knext.LocalPathParameter(
        label="Model Path",
        description="Enter the path to the simulation model file. The required file format and path syntax depend on the simulation tool being executed.",
        placeholder_text="my/path/model"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.OTHER.name]),  knext.Effect.SHOW)

    # validation for Other (CMD-based) model path
    @other_model_path.validator
    def validate_other_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return

    # CMD command for Other tool execution
    other_cmd_command = knext.StringParameter(
        label="CMD Command",
        description="Enter the command used to execute the simulation tool. Use placeholders like {model_path} to reference the model file path dynamically.",
        default_value=""
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.OTHER.name]), knext.Effect.SHOW)

    # SimPy model path
    simpy_model_path = knext.LocalPathParameter(
        label="Model Path",
        description="Enter the path to the SimPy simulation script (.py). The script must support a --help flag exposing its arguments and default values.",
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
        description="Select how the simulation writes its results: directly to a file on disk or to a connected database.",
        default_value=pdef.SimulationOutputType.FILEBASED.name,
        enum=pdef.SimulationOutputType,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    )

    # output file name
    output_file = knext.StringParameter(
        label="Output Filename",
        description="Name of the file to be generated (e.g. results.csv).",
        default_value="output.csv"
    ).rule(knext.OneOf(simulation_output, [pdef.SimulationOutputType.FILEBASED.name]), knext.Effect.SHOW)
    
    # configuration time logic
    def configure(self, configure_context):
        port_numbers  = configure_context.get_connected_output_port_numbers()

        if self.tool_choice == pdef.SimTools.SIMPY.name:
            if port_numbers[1] < 1:
                raise ValueError("SimPy requires at least one connected output port in the 'SimPy Arguments' group to provide input arguments.")
        else:
            if port_numbers[1] > 0:
                raise ValueError("Please delete all connected output ports in the 'Simpy Arguments' group.")
        
        return (
            port.SimulationModelSpec(), 
            [knext.Schema(names=[], ktypes=[])]*port_numbers[1],
        )

    # main execution logic
    def execute(self, exec_context):
        import os
        import shutil
        import re
        import json
        import sys
        import subprocess
        import pandas as pd
        import datetime

        # path Mapping
        tool_paths = {
            pdef.SimTools.ANYLOGIC.name: self.anylogic_model_path,
            pdef.SimTools.OTHER.name: self.other_model_path,
            pdef.SimTools.SIMPY.name: self.simpy_model_path
        }
        
        selected_path = tool_paths.get(self.tool_choice, "")
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if not selected_path or not os.path.isfile(selected_path):
            raise FileNotFoundError(f"Model file not found: {selected_path}")

        # workspace navigation
        workflow_data_dir = exec_context.get_workflow_data_area_dir()
        workspace_folder_dir = os.path.abspath(os.path.join(workflow_data_dir, "..", ".."))
        created_folder_dir = os.path.join(workspace_folder_dir, "Resources", f"{self.tool_choice}_{now}")

        exec_context.flow_variables.update({
            "simulation_tool": self.tool_choice,
            "output_mode": self.simulation_output,
            "workflow_folder_dir": workspace_folder_dir,
            "resource_folder": created_folder_dir
        })

        if self.tool_choice == pdef.SimTools.OTHER.name:
            exec_context.flow_variables["cmd_command"] = self.other_cmd_command

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

        port_numbers = exec_context.get_connected_output_port_numbers()

        # return values
        if self.tool_choice == pdef.SimTools.SIMPY.name and argument_defaults:
            df_meta = pd.DataFrame.from_dict(argument_defaults)
            df_meta = df_meta.apply(pd.to_numeric, errors='ignore')
            return (
                port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res), 
                [knext.Table.from_pandas(df_meta)] *port_numbers[1],
            )
        
        return (
            port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res), 
            [knext.Table.from_pandas(pd.DataFrame())] * port_numbers[1],
        )