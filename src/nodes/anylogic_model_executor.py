import logging
import knime.extension as knext
from utils import port
from sim_ext import main_category

LOGGER = logging.getLogger(__name__)


@knext.node(
    name="AnyLogic Model Executor",
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
class AnyLogicModelExecutor:
    """Execute an AnyLogic simulation model within a KNIME workflow.

    This node receives an AnyLogic model reference and an optional table of configuration
    parameters or DoE factor combinations, then launches the simulation via the
    platform-specific execution script bundled with the model export.

    ### Features:
    - Launches the model via a `.bat` (Windows) or `.sh` (Unix) script.
    - Relocates output files to a structured `results/` directory.
    - Sets `output_file_path` as a flow variable pointing to the generated result file.
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
            exec_context.flow_variables["output_file_path"] = execute_simulation.run_anylogic(
                exec_context, input_2, resource_folder
            )
        except Exception as e:
            LOGGER.error(f"AnyLogic execution failed: {e}")
            raise
