import logging
import knime.extension as knext
from utils import simulation_port as sp
import os
import platform
import pandas as pd
import shutil
import subprocess

# setup logger
LOGGER = logging.getLogger(__name__)

# define the KNIME node
@knext.node(
    name="Simulation Model Executor",
    node_type=knext.NodeType.SINK,
    icon_path="icons/model.png",
    category="/community/simulation"
)

@knext.input_port(name="Test", description="...", port_type=sp.simulation_port_type)

class ModelExecutorCustom:
    """Short one-line description of the node.
        ...
    """

    # configuration-time logic
    def configure(self, configure_context, input_schema_1):
        configure_context.set_warning("This is a warning during configuration")

    # main execution logic
    def execute(self, exec_context, input_1: sp.SimulationModelPort):
        # get the file system path of the simulation model input
        model_path = input_1.path

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")

        # get the operating system name and the path to the resource folder from flow variables
        os_name = platform.system()
        resource_folder = exec_context.flow_variables.get("resource_folder")

        if not os_name or not resource_folder:
            raise ValueError("Missing required flow variables: 'os_name' and/or 'resource_folder'.")        

        if not os.path.exists(resource_folder):
            raise FileNotFoundError(f"Resource folder not found: {resource_folder}")

        # retrieve the selected simulation tool from flow variables
        simulation_tool = exec_context.flow_variables.get("simulation_tool")

        if simulation_tool == "ANYLOGIC":
            if os_name == "Windows":
                # locate and run the first .bat file found in the resource folder
                bat_files = [f for f in os.listdir(resource_folder) if f.endswith(".bat")]
                if not bat_files:
                    raise FileNotFoundError("No .bat file found in the resource folder.")

                bat_path = os.path.join(resource_folder, bat_files[0])
                LOGGER.info(f"Executing Windows batch file: {bat_path}")

                subprocess.run(["cmd.exe", "/c", bat_path], check=True)

            elif os_name == "Linux":
                # locate and run the first .sh file found in the resource folder
                sh_files = [f for f in os.listdir(resource_folder) if f.endswith(".sh")]
                if not sh_files:
                    raise FileNotFoundError("No .sh file found in the resource folder.")

                sh_path = os.path.join(resource_folder, sh_files[0])
                LOGGER.info(f"Executing Linux shell script: {sh_path}")

                # ensure the shell script has executable permissions before running
                os.chmod(sh_path, 0o755)
                subprocess.run([sh_path], check=True)

            else:
                raise ValueError(f"Unsupported operating system: {os_name}")
        elif simulation_tool == "ASAP":
            print("hello world")
            #do some magic
        elif simulation_tool == "SIMPY":
            print("hello world")
            #do some magic
        else: 

            #comment

            return