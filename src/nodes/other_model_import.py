import logging
import knime.extension as knext
from utils import port
from sim_ext import main_category

LOGGER = logging.getLogger(__name__)


@knext.node(
    name="Simulation Model Importer (CMD-based)",
    node_type=knext.NodeType.SOURCE,
    icon_path="icons/simulation_import.png",
    category=main_category,
)
@knext.output_port(
    name="Output Data",
    description="Result of simulation model setup.",
    port_type=port.simulation_port_type,
)
class OtherModelImporter:
    """Import a simulation model for CMD-based execution and prepare it within a KNIME workflow.

    This node registers any simulation tool executable via a custom command-line call
    and copies its files into a structured resource directory inside the KNIME workspace.
    Configuration values are passed downstream as flow variables.

    ### Features:
    - Accepts any model file format — no file-extension constraint.
    - Accepts a custom CMD command with a `{model_path}` placeholder for dynamic path injection.
    - Creates a timestamped `Resources/` directory in the KNIME workspace.
    - Exports key settings (tool, model path, CMD command) as flow variables.
    """

    other_model_path = knext.LocalPathParameter(
        label="Model Path",
        description="Enter the path to the simulation model file. The required file format and path syntax depend on the simulation tool being executed.",
        placeholder_text="my/path/model",
    )

    @other_model_path.validator
    def validate_other_model_path(path: str):
        if not path:
            return

    other_cmd_command = knext.StringParameter(
        label="CMD Command",
        description="Enter the command used to execute the simulation tool. Use placeholders like {model_path} to reference the model file path dynamically.",
        default_value="",
    )

    def configure(self, configure_context):
        return port.SimulationModelSpec()

    def execute(self, exec_context):
        import os
        import shutil
        import datetime

        selected_path = self.other_model_path
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if not selected_path or not os.path.isfile(selected_path):
            raise FileNotFoundError(f"Model file not found: {selected_path}")

        workflow_data_dir = exec_context.get_workflow_data_area_dir()
        workspace_folder_dir = os.path.abspath(os.path.join(workflow_data_dir, "..", ".."))
        created_folder_dir = os.path.join(workspace_folder_dir, "Resources", f"OTHER_{now}")

        exec_context.flow_variables.update({
            "simulation_tool": "OTHER",
            "workflow_folder_dir": workspace_folder_dir,
            "resource_folder": created_folder_dir,
            "cmd_command": self.other_cmd_command,
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

        return port.SimulationModelPort(port.SimulationModelSpec(), model_path_in_res)
