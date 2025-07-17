import logging
from typing import TextIO, BinaryIO
from utils import simulation_port as sp, parameter_definition as pdef
import knime.extension as knext
import pandas as pd


# setup logger
LOGGER = logging.getLogger(__name__)
    
# define the KNIME node
@knext.node(
    name="Simulation Model Importer",
    node_type=knext.NodeType.SOURCE,
    icon_path="icons/model.png",
    category="/community/simulation"
)

@knext.output_port(name="Output Data", description="Result of simulation model setup.", port_type=sp.simulation_port_type)
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
        description="Enter a path to the model.jar. The required syntax of the path depends on the chosen file system.",
        placeholder_text="my/path/model.jar"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.ANYLOGIC.name]), knext.Effect.SHOW)

    # validation for AnyLogic model path
    @anylogic_model_path.validator
    def validate_al_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith("model.jar"):
            raise ValueError ("Invalid path: must end with 'model.jar'")

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

    # output file name for SimPy
    simpy_output = knext.StringParameter(
        label="Output file",
        description="File name",
        default_value="simpy_output.csv"
    ).rule(knext.OneOf(tool_choice, [pdef.SimTools.SIMPY.name]), knext.Effect.SHOW)

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

        # simulation tool metadata as flow variables
        exec_context.flow_variables["simulation_tool"] = self.tool_choice

        # handle tool-specific model path and flow variable setup
        model_path = ""

        if self.tool_choice == pdef.SimTools.ANYLOGIC.name:
            model_path = self.anylogic_model_path
        elif self.tool_choice == pdef.SimTools.ASAP.name:
            model_path = self.asap_model_path
        elif self.tool_choice == pdef.SimTools.SIMPY.name:
            model_path = self.simpy_model_path

        # derive paths for resource and workspace directories
        workflow_data_dir = exec_context.get_workflow_data_area_dir()
        workspace_folder_dir = os.path.dirname(os.path.dirname(workflow_data_dir))
        exec_context.flow_variables["workflow_folder_dir"] = workspace_folder_dir

        # prepare the resource folder
        created_folder_dir = os.path.join(workspace_folder_dir, "Resources")
        os.makedirs(created_folder_dir, exist_ok=True)
        exec_context.flow_variables["resource_folder"] = created_folder_dir
    
        # copy model files to the resource folder
        if model_path:
            # empty folder
            for filename in os.listdir(created_folder_dir):
                file_path = os.path.join(created_folder_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    LOGGER.error(f"Error deleting {file_path}: {e}")

            # copy files from model path
            model_dir = os.path.dirname(model_path)

            for item in os.listdir(model_dir):
                src = os.path.join(model_dir, item)
                dst = os.path.join(created_folder_dir, item)
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                        LOGGER.warning(f"Copy folder: {src} -> {dst}")
                    elif os.path.isfile(src):
                        shutil.copy2(src, dst)
                        LOGGER.warning(f"Copy file: {src} -> {dst}")
                except Exception as e:
                    LOGGER.error(f"Error copying {src} to {dst}: {e}")

        # validate model path exists before proceeding
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # model path in resource folder
        model_path = os.path.join(created_folder_dir, os.path.basename(model_path))
        exec_context.flow_variables["model_path"] = model_path

        if self.tool_choice == pdef.SimTools.SIMPY.name:

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"SimPy script not found in resource folder: {model_path}")

            try:
                result = subprocess.run(
                    ["python", model_path, "--help"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                help_output = result.stdout.strip() or result.stderr.strip()
                LOGGER.info(f"SimPy script help output:\n{help_output}")

                # extract arguments and their default values from help output
                lines = help_output.splitlines()

                # Only consider lines after the "options:" section
                try:
                    start_index = next(i for i, line in enumerate(lines) if line.strip().lower() == "options:")
                    option_lines = lines[start_index + 1:]
                except StopIteration:
                    option_lines = lines  # fallback: parse all lines if 'options:' not found

                # Combine wrapped lines into full logical lines
                merged_lines = []
                current = ""

                for line in option_lines:
                    if line.strip().startswith("--"):
                        if current:
                            merged_lines.append(current)
                        current = line.strip()
                    elif current:
                        current += " " + line.strip()
                if current:
                    merged_lines.append(current)

                # Now extract args with defaults
                pattern = r"--([\w\-]+)[^\n]*\(default:\s*([^)]+)\)"
                argument_defaults = {
                    match.group(1): [match.group(2).strip()]
                    for line in merged_lines
                    if (match := re.search(pattern, line))
                }

                exec_context.flow_variables["simpy_help_output"] = json.dumps(argument_defaults)
                LOGGER.info(f"Extracted SimPy defaults: {argument_defaults}")

            except subprocess.CalledProcessError as e:
                LOGGER.error(f"Error while executing SimPy script with --help: {e.stderr}")
                raise

        if self.tool_choice == pdef.SimTools.SIMPY.name:
            # convert to DataFrame
            df_meta = pd.DataFrame.from_dict(argument_defaults)

            for col in df_meta.columns:
                try:
                    df_meta[col] = pd.to_numeric(df_meta[col], errors="raise")
                except Exception:
                    # Falls Umwandlung fehlschlägt, bleibe bei string
                    df_meta[col] = df_meta[col].astype(str)

            return sp.SimulationModelPort(sp.SimulationModelSpec(), model_path), knext.Table.from_pandas(df_meta)
        else:
            return sp.SimulationModelPort(sp.SimulationModelSpec(), model_path), knext.Table.from_pandas(pd.DataFrame())