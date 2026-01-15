import os
import subprocess
import platform
import logging
import sys
import shutil

# initialize the logger for the module
logger = logging.getLogger(__name__)

# define supported file extensions for output handling
allowed_extensions = (".csv", ".txt", ".xlsx", ".xls")

def _get_current_date_string():
    # fetch the current system date using subprocess to avoid importing additional packages
    # uses powershell on windows and the date command on unix-based systems
    try:
        if platform.system() == "Windows":
            cmd = ["powershell", "-command", "get-date -format 'yyyy-MM-dd'"]
        else:
            cmd = ["date", "+%y-%m-%d"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        # fallback string if the system command fails
        return "unknown_date"

def _get_paths(exec_context, input_2, resource_folder, tool):
    # consolidate path logic and determine the experiment naming convention
    # extracts experiment and configuration names from knime flow variables or input tables
    experiment = exec_context.flow_variables.get("experiment", "default_experiment")
    config_value = "unnamed_config"

    if input_2 is not None:
        df = input_2.to_pandas()
        if not df.empty:
            if "experiment" in [c.lower() for c in df.columns]:
                # search for the experiment column regardless of casing
                col_name = [c for c in df.columns if c.lower() == "experiment"][0]
                val = df.iloc[0][col_name]
                if isinstance(val, str) and val.strip():
                    experiment = val
            
            # get configuration name for fallback file naming
            config_value = df.iloc[0].get("CONFIGURATION", "unnamed_config")

    # append the current date suffix if the run is identified as a default experiment
    if "default" in experiment.lower():
        today = _get_current_date_string()
        experiment = f"{experiment}_{today}"

    # define the target directory within a results folder next to resources
    norm_res = os.path.normpath(resource_folder)
    parent_dir = os.path.dirname(norm_res)
    experiment_dir = os.path.join(parent_dir, "results", tool, experiment)
    
    # ensure the results directory exists
    os.makedirs(experiment_dir, exist_ok=True)
    
    return experiment, config_value, experiment_dir

def run_anylogic(exec_context, input_2, resource_folder):
    # execute anylogic simulation using platform-specific scripts and relocate outputs
    _, config_value, experiment_dir = _get_paths(exec_context, input_2, resource_folder, "AnyLogic")
    
    # check for existence of the source resource folder
    if not os.path.exists(resource_folder):
        raise filenotfounderror(f"resource folder not found: {resource_folder}")

    # identify the correct execution script based on the operating system
    os_name = platform.system()
    script_ext = ".bat" if os_name == "windows" else ".sh"
    scripts = [f for f in os.listdir(resource_folder) if f.endswith(script_ext)]
    
    if not scripts:
        raise filenotfounderror(f"no {script_ext} file found in {resource_folder}")
    
    script_path = os.path.join(resource_folder, scripts[0])
    
    # prepare the command and set execution permissions for unix systems
    if os_name == "windows":
        cmd = ["cmd.exe", "/c", script_path]
    else:
        os.chmod(script_path, 0o755)
        cmd = ["/bin/bash", script_path] if os_name == "darwin" else [script_path]

    logger.info(f"starting anylogic simulation: {script_path}")
    
    # run simulation using the resource folder as the working directory
    subprocess.run(cmd, check=True, cwd=resource_folder)

    # determine the expected output filename from flow variables or default configuration
    flow_out = exec_context.flow_variables.get("output_file", "")
    
    # find the appropriate extension by checking against allowed formats
    target_ext = ".csv"
    for ext in allowed_extensions:
        if flow_out.lower().endswith(ext):
            target_ext = ext
            break

    # build the source and destination paths for file relocation
    raw_filename = os.path.basename(flow_out) if flow_out else f"{config_value}{target_ext}"
    source_path = os.path.join(resource_folder, raw_filename)
    dest_path = os.path.join(experiment_dir, raw_filename)

    # move the generated file or attempt to find alternative results in the folder
    if os.path.exists(source_path):
        shutil.move(source_path, dest_path)
        logger.info(f"moved output to: {dest_path}")
    else:
        logger.warning(f"primary output not found, scanning for alternative result files")
        for f in os.listdir(resource_folder):
            if f.lower().endswith(allowed_extensions):
                shutil.move(os.path.join(resource_folder, f), os.path.join(experiment_dir, f))
                logger.info(f"auto-detected and moved: {f}")

    return dest_path

def run_asap(exec_context, model_path, resource_folder):
    # execute autosched ap simulation with duration parameters
    if not os.path.exists(model_path):
        raise filenotfounderror(f"asap model file missing: {model_path}")

    # retrieve simulation duration from knime flow variables
    asap_days = exec_context.flow_variables.get("asap_days")
    if asap_days is None:
        raise valueerror("missing flow variable: asap_days")

    # extract model name without extension for the command line interface
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    cmd = ["asap", f"-d{asap_days}", model_name]

    logger.info(f"executing asap model: {' '.join(cmd)}")
    try:
        # run the command and capture output for logging
        proc = subprocess.run(cmd, cwd=resource_folder, capture_output=True, text=True, check=True)
        if proc.stdout:
            logger.info(f"asap output: {proc.stdout}")
    except subprocess.calledprocesserror as e:
        logger.error(f"asap execution failed: {e.stderr}")
        raise

def run_simpy(exec_context, input_2, model_path, resource_folder):
    # run simpy simulation and map input table columns to command line arguments
    _, config_value, experiment_dir = _get_paths(exec_context, input_2, resource_folder, "SimPy")
    simpy_args = []
    val = ''

    if input_2 is not None:
        df = input_2.to_pandas()
        if df.empty:
            raise valueerror("input table is empty")

        row = df.iloc[0]
        
        # determine the preferred file extension for the output
        flow_out = exec_context.flow_variables.get("output_file", "")
        fallback_ext = ".csv"
        for ext in allowed_extensions:
            if flow_out.lower().endswith(ext):
                fallback_ext = ext
                break

        output_set = False
        # iterate through columns to build command line flags
        for col in df.columns:
            if col.upper() in {"EXPERIMENT", "CONFIGURATION"}:
                continue
            
            val = row[col]
            # redirect output path to the specific experiment directory
            if col.lower() == "output":
                if isinstance(val, str) and val.lower().endswith(allowed_extensions):
                    val = os.path.join(experiment_dir, os.path.basename(val))
                    output_set = True
                else:
                    continue
            
            # ensure whole numbers are passed as integers rather than floats
            elif isinstance(val, float) and val.is_integer():
                val = int(val)

            simpy_args.extend([f"--{col}", str(val)])

        # ensure an output argument is present even if not defined in the table
        if not output_set:
            simpy_args.extend(["--output", os.path.join(experiment_dir, f"{config_value}{fallback_ext}")])
    else:
        # handle case where only flow variables are used for simulation arguments
        raw_output = exec_context.flow_variables.get("output_file")
        if raw_output:
            parts = raw_output.split()
            if "--output" in parts:
                idx = parts.index("--output") + 1
                if idx < len(parts):
                    # update the output path within the argument list
                    parts[idx] = os.path.join(experiment_dir, os.path.basename(parts[idx]))
            simpy_args = parts

    # assemble the final command using the current python interpreter
    cmd = [sys.executable, model_path] + simpy_args
    logger.info(f"running simpy model: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    return simpy_args[1]