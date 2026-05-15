import logging
import knime.extension as knext
from utils import port
from sim_ext import main_category

LOGGER = logging.getLogger(__name__)


@knext.node(
    name="Simulation Model Executor (CMD-based)",
    node_type=knext.NodeType.SINK,
    icon_path="icons/simulation_execution.png",
    category=main_category,
)
@knext.input_port(
    name="Simulation Model",
    description="The simulation model input port containing a reference to the model file",
    port_type=port.simulation_port_type,
)
@knext.input_table(
    name="Configuration Table",
    description="Optional input table containing simulation parameters or DoE configurations",
    optional=True,
)
class OtherModelExecutor:
    """Execute a CMD-based simulation model within a KNIME workflow.

    This node receives a simulation model reference and executes the user-defined CMD
    command configured in the Other Model Importer. The `{model_path}` placeholder in
    the command is resolved to the actual model file path at runtime.

    ### Features:
    - Executes any simulation tool via a fully customizable shell command.
    - Runs the command in the resource folder as the working directory.
    - Logs stdout output for inspection.
    """

    def configure(self, configure_context, input_schema_1, input_schema_2):
        pass

    def execute(self, exec_context, input_1: port.SimulationModelPort, input_2):
        import os
        from utils import execute_simulation

        model_path = input_1.path
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")

        resource_folder = exec_context.flow_variables.get("resource_folder")
        if not resource_folder or not os.path.exists(resource_folder):
            raise FileNotFoundError(f"Resource folder not found: {resource_folder}")

        try:
            execute_simulation.run_other(exec_context, model_path, resource_folder)
        except Exception as e:
            LOGGER.error(f"CMD-based execution failed: {e}")
            raise
