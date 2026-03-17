import logging
import knime.extension as knext
from utils import port
from sim_ext import main_category
import pandas as pd

# setup logger
LOGGER = logging.getLogger(__name__)

# define the KNIME node
@knext.node(
    name="Simulation Model Executor",
    node_type=knext.NodeType.SINK,
    icon_path="icons/simulation_execution.png",
    category=main_category
)

@knext.input_port(
    name="Simulation Model", 
    description="The simulation model input port containing a reference to the model file", 
    port_type=port.simulation_port_type
)

@knext.input_table(
    name="Configuration Table", 
    description="Optional input table containing simulation parameters or DoE configurations", 
    optional=True
)

class ModelExecutorCustom:
    """Execute a simulation model using the tool configured in the Simulation Model Importer.

    This node receives a simulation model reference and an optional table of configuration
    parameters or DoE factor combinations, then triggers the corresponding simulation run.
    Execution behavior adapts automatically based on the simulation tool set via flow variables.

    ### Supported Tools:
    - **AnyLogic**: Launches the model via a platform-specific script and relocates output files.
    - **SimPy**: Runs the Python script with command-line arguments derived from the input table.
    - **Other (CMD-based)**: Executes the user-defined CMD command with the resolved model path.

    """

    # configuration-time logic
    def configure(self, configure_context, input_schema_1, input_schema_2):
        #configure_context.set_warning(input_schema_1.path)

        configure_context.set_warning("This is a warning during configuration")

    # main execution logic
    def execute(self, exec_context, input_1: port.SimulationModelPort, input_2):
        import os
        import platform
        from utils import execute_simulation

        # get the file system path of the simulation model input (and the AnyLogic IDE)
        model_path = input_1.path

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")

        # get the operating system name and the path to the resource folder from flow variables
        os_name = platform.system()
        resource_folder = exec_context.flow_variables.get("resource_folder")

        if not os_name or not resource_folder:
            raise ValueError("Missing required flow variables: 'os_name' and/or 'resource_folder'")        

        if not os.path.exists(resource_folder):
            raise FileNotFoundError(f"Resource folder not found: {resource_folder}")

        # retrieve the selected simulation tool from flow variables
        simulation_tool = exec_context.flow_variables.get("simulation_tool")

        if simulation_tool == "ANYLOGIC":
            try:
                exec_context.flow_variables["output_file_path"] = execute_simulation.run_anylogic(exec_context, input_2, resource_folder)
            except Exception as e:
                LOGGER.error(f"AnyLogic execution failed: {e}")
                raise

        elif simulation_tool == "OTHER":
            try:
                execute_simulation.run_other(exec_context, model_path, resource_folder)
            except Exception as e:
                LOGGER.error(f"CMD-based execution failed: {e}")
                raise

        elif simulation_tool == "SIMPY":
            try:
                exec_context.flow_variables["output_file_path"] = execute_simulation.run_simpy(exec_context, input_2, model_path, resource_folder)
            except Exception as e:
                LOGGER.error(f"SimPy execution failed: {e}")
                raise

        else:
            # handle unknown or unsupported simulation tool values
            LOGGER.error(f"Unsupported simulation tool: {simulation_tool}")
            raise ValueError(f"Simulation tool '{simulation_tool}' is not supported")

        return