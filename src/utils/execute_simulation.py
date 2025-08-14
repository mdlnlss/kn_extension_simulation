import os
import subprocess
import platform
import logging

LOGGER = logging.getLogger(__name__)

# function to execute AnyLogic simulation via platform-specific script
def run_anylogic(model_path, anylogic_path, resource_folder):
    os_name = platform.system()

    if model_path.endswith(".alp"):
        # Validate AnyLogic IDE path
        if not os.path.exists(anylogic_path):
            raise FileNotFoundError(f"AnyLogic executable not found: {anylogic_path}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"AnyLogic .alp model not found: {model_path}")
        
        LOGGER.info(f"Launching AnyLogic IDE with model: {model_path}")
        try:
            subprocess.run([anylogic_path, '-r', model_path, "Simulation"], check=True)
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"Failed to launch AnyLogic IDE: {e}")
            raise
    else:
        if not os.path.exists(resource_folder):
            raise FileNotFoundError(f"Resource folder not found: {resource_folder}")

        if os_name == "Windows":
            # look for .bat scripts in the resource folder
            bat_files = [f for f in os.listdir(resource_folder) if f.endswith(".bat")]
            if not bat_files:
                raise FileNotFoundError("No .bat file found in the resource folder.")

            bat_path = os.path.join(resource_folder, bat_files[0])
            LOGGER.info(f"Executing Windows batch file: {bat_path}")

            # execute the batch file
            subprocess.run(["cmd.exe", "/c", bat_path], check=True)

        elif os_name == "Linux":
            # look for .sh scripts in the resource folder
            sh_files = [f for f in os.listdir(resource_folder) if f.endswith(".sh")]
            if not sh_files:
                raise FileNotFoundError("No .sh file found in the resource folder.")

            sh_path = os.path.join(resource_folder, sh_files[0])
            LOGGER.info(f"Executing Linux shell script: {sh_path}")

            # ensure shell script has execution permissions
            os.chmod(sh_path, 0o755)
            subprocess.run([sh_path], check=True)

        else:
            raise ValueError(f"Unsupported operating system: {os_name}")

# function to execute AutoSched AP simulation
def run_asap(exec_context, model_path, resource_folder):
    import subprocess as sp

    # ensure the specified model file exists
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"ASAP model file not found at: {model_path}")

    # ensure the resource folder exists
    if not os.path.isdir(resource_folder):
        raise FileNotFoundError(f"Resource folder not found: {resource_folder}")

    # retrieve required flow variable that defines the number of simulation days
    asap_days = exec_context.flow_variables.get("asap_days")
    if asap_days is None:
        raise ValueError("Missing flow variable: 'asap_days'")

    # extract model name (without extension) to use in the ASAP CLI command
    model_filename = os.path.basename(model_path)
    model_name, _ = os.path.splitext(model_filename)

    # construct the ASAP command
    # -d[Integer:x] defines the simulation duration
    # [model_name] refers to the simulation model file (by name, not full path)
    cmd = [
        "asap",
        f"-d{asap_days}",
        f"{model_name}"
    ]

    LOGGER.info(f"Executing ASAP model: {' '.join(cmd)}")
    try:
        # run the command inside the resource folder context
        # set working directory to where the model and resources are
        # capture stdout and stderr
        # decode output as text instead of bytes
        # raise an error if return code is non-zero
        proc = sp.run(
            cmd,
            cwd=resource_folder,         
            capture_output=True,
            text=True,                   
            check=True                   
        )

        # log standard output
        LOGGER.info(f"ASAP output:\n{proc.stdout}")

        # optionally log standard error if any
        if proc.stderr:
            LOGGER.warning(f"ASAP stderr:\n{proc.stderr}")

    except sp.CalledProcessError as e:
        # if subprocess fails, log the error output and re-raise the exception
        LOGGER.error(f"ASAP execution failed:\n{e.stderr}")
        raise

# function to execute a SimPy simulation script with parameter mapping from KNIME inputs and flow variables
def run_simpy(exec_context, input_2, model_path, resource_folder):
    simpy_args = []  # argument list to pass to the SimPy script

    # get experiment name from flow variable or table
    experiment = exec_context.flow_variables.get("experiment", "default_experiment")

    # if input table is provided and contains experiment name, override flow variable
    if input_2 is not None:
        df = input_2.to_pandas()
        if not df.empty and "EXPERIMENT" in df.columns:
            experiment_from_table = df.iloc[0]["EXPERIMENT"]
            if isinstance(experiment_from_table, str) and experiment_from_table.strip():
                experiment = experiment_from_table

    # prepare the experiment-specific output folder
    experiment_dir = os.path.join(resource_folder, experiment)
    os.makedirs(experiment_dir, exist_ok=True)

    if input_2 is not None:
        df = input_2.to_pandas()

        if df.empty:
            raise ValueError("Input table is empty.")

        # take first configuration row
        row = df.iloc[0]
        configuration_value = row.get("CONFIGURATION", "unnamed_config")

        # get default output name and determine fallback file extension
        simpy_output = exec_context.flow_variables.get("simpy_output", "")
        fallback_ext = ".csv"
        for ext in [".csv", ".txt"]:
            if ext in simpy_output:
                fallback_ext = ext
                break

        output_set = False

        # convert each relevant column in the row into a CLI argument
        for col in df.columns:
            if col.upper() not in {"EXPERIMENT", "CONFIGURATION"}:
                value = row[col]

                # handle user-defined output file if present
                if col.lower() == "output":
                    if isinstance(value, str) and value.strip().lower().endswith((".csv", ".txt")):
                        value = os.path.join(experiment_dir, os.path.basename(value))
                        output_set = True
                    else:
                        continue  # skip invalid output entries

                # cast float values that are whole numbers to integers
                elif isinstance(value, float) and value.is_integer():
                    value = int(value)

                simpy_args.append(f"--{col}")
                simpy_args.append(str(value))

        # if no output argument was defined explicitly, create a fallback one
        if not output_set:
            generated_output = os.path.join(experiment_dir, f"{configuration_value}{fallback_ext}")
            simpy_args.append("--output")
            simpy_args.append(generated_output)
            LOGGER.info(f"Generated fallback output: {generated_output}")

    else:
        # no table input, try to pull full argument string from flow variable
        simpy_output = exec_context.flow_variables.get("simpy_output")
        if not simpy_output:
            raise ValueError("Missing flow variable: simpy_output")

        # attempt to redirect output file into experiment folder if present
        if "--output" in simpy_output:
            parts = simpy_output.split()
            output_idx = parts.index("--output") + 1 if "--output" in parts else -1
            if 0 < output_idx < len(parts):
                raw_filename = os.path.basename(parts[output_idx])
                redirected_path = os.path.join(experiment_dir, raw_filename)
                parts[output_idx] = redirected_path
                simpy_args = parts
            else:
                simpy_args = simpy_output.split()
        else:
            simpy_args = simpy_output.split()

    # construct full command and execute the simulation script
    cmd = ["python", model_path] + simpy_args
    LOGGER.info(f"Running SimPy model: {' '.join(cmd)}")

    subprocess.run(cmd, check=True)