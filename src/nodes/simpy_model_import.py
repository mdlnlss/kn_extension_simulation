import logging
import knime.extension as knext
from utils import parameter_utils as pdef, port
from sim_ext import main_category
import pandas as pd

LOGGER = logging.getLogger(__name__)


@knext.node(
    name="SimPy Model Importer",
    node_type=knext.NodeType.SOURCE,
    icon_path="icons/simulation_import.png",
    category=main_category,
)
@knext.output_port(
    name="Output Data",
    description="Result of simulation model setup.",
    port_type=port.simulation_port_type,
)
@knext.output_table(
    name="SimPy Arguments",
    description="A table pre-filled with the default argument values parsed from the SimPy model's --help output.",
)
class SimPyModelImporter:
    """Import a SimPy simulation model and prepare it for execution within a KNIME workflow.

    This node registers a SimPy `.py` simulation script and copies its files into a
    structured resource directory inside the KNIME workspace. The script is invoked with
    `--help` to extract default argument values, which are passed downstream as a table.

    ### Features:
    - Validates that the model file is a `.py` script.
    - Parses `--help` output to extract argument defaults automatically.
    - Supports file-based or database output modes.
    - Creates a timestamped `Resources/` directory in the KNIME workspace.
    - Exports key settings (tool, model path, output mode, parsed arguments) as flow variables.
    """

    simpy_model_path = knext.LocalPathParameter(
        label="Model Path",
        description="Enter the path to the SimPy simulation script (.py). The script must support a --help flag exposing its arguments and default values.",
        placeholder_text="my/path/model.py",
    )

    @simpy_model_path.validator
    def validate_simpy_model_path(path: str):
        if not path:
            return
        if not path.endswith(".py"):
            raise ValueError("Invalid path: must end with '.py'")

    simulation_output = knext.EnumParameter(
        label="Output Type",
        description="Select how the simulation writes its results: directly to a file on disk or to a connected database.",
        default_value=pdef.SimulationOutputType.FILEBASED.name,
        enum=pdef.SimulationOutputType,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    )

    output_file = knext.StringParameter(
        label="Output Filename",
        description="Name of the file to be generated (e.g. results.csv).",
        default_value="output.csv",
    ).rule(
        knext.OneOf(simulation_output, [pdef.SimulationOutputType.FILEBASED.name]),
        knext.Effect.SHOW,
    )

    def configure(self, configure_context):
        return (
            port.SimulationModelSpec(),
            knext.Schema(names=[], ktypes=[]),
        )

    def execute(self, exec_context):
        import os
        import shutil
        import re
        import json
        import sys
        import subprocess
        import datetime

        selected_path = self.simpy_model_path
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if not selected_path or not os.path.isfile(selected_path):
            raise FileNotFoundError(f"Model file not found: {selected_path}")

        workflow_data_dir = exec_context.get_workflow_data_area_dir()
        workspace_folder_dir = os.path.abspath(os.path.join(workflow_data_dir, "..", ".."))
        created_folder_dir = os.path.join(workspace_folder_dir, "Resources", f"SIMPY_{now}")

        exec_context.flow_variables.update({
            "simulation_tool": "SIMPY",
            "output_mode": self.simulation_output,
            "workflow_folder_dir": workspace_folder_dir,
            "resource_folder": created_folder_dir,
        })

        os.makedirs(created_folder_dir, exist_ok=True)
        model_dir = os.path.dirname(selected_path)
        try:
            shutil.copytree(model_dir, created_folder_dir, dirs_exist_ok=True)
            LOGGER.info(f"Updated resources in {created_folder_dir}")
        except Exception as e:
            LOGGER.warning(f"Could not overwrite some files in {created_folder_dir}: {e}")

        model_path_in_res = os.path.join(created_folder_dir, os.path.basename(selected_path))
        exec_context.flow_variables["model_path"] = model_path_in_res

        argument_defaults = {}
        try:
            result = subprocess.run(
                [sys.executable, model_path_in_res, "--help"],
                capture_output=True, text=True, check=True,
            )
            help_output = result.stdout or result.stderr
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

        if argument_defaults:
            df_meta = pd.DataFrame.from_dict(argument_defaults)
            df_meta = df_meta.apply(pd.to_numeric, errors="ignore")
            return (
                port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res),
                knext.Table.from_pandas(df_meta),
            )

        return (
            port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res),
            knext.Table.from_pandas(pd.DataFrame()),
        )
