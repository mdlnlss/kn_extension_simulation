import logging
import knime.extension as knext
from utils import port
from sim_ext import main_category

LOGGER = logging.getLogger(__name__)


@knext.node(
    name="SimPy Model Executor",
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
class SimPyModelExecutor:
    """Execute a SimPy simulation model within a KNIME workflow.

    This node receives a SimPy model reference and an optional table of configuration
    parameters or DoE factor combinations, then runs the Python script with the
    corresponding command-line arguments derived from the input table.

    ### Features:
    - Maps input table columns to `--flag value` command-line arguments.
    - Redirects the `--output` argument to the structured `results/` directory.
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
            exec_context.flow_variables["output_file_path"] = execute_simulation.run_simpy(
                exec_context, input_2, model_path, resource_folder
            )
        except Exception as e:
            LOGGER.error(f"SimPy execution failed: {e}")
            raise
