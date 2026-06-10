> **Work in Progress**

# Simulation Study Extension for KNIME

[![KNIME Hub](https://img.shields.io/badge/KNIME%20Hub-View%20on%20Hub-blue?style=flat-square)](https://hub.knime.com/) <!-- TODO: Add Hub Link -->
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
> *(<- TODO: Replace with actual Hub link)*

This repository is the home of the Simulation Study Extension for KNIME Analytics Platform. The extension provides a set of nodes for Design of Experiments (DoE) and simulation model execution.

The extension is developed by [Madlene Leißau](https://de.linkedin.com/in/madlene-leissau) from the Research Group [Industry Analytics](www.industry-analytics.de) at the [University of Applied Sciences Zwickau](www.whz.de) and [KNIME](www.knime.com) as part of a Proof of Concept (PoC). The goal of the collaboration is to develop KNIME Analytics Platform extensions and best-practice workflows to provide a consistent and compatible platform for simulation studies across disciplines and simulation tools.

## Nodes

This extension provides a suite of nodes to facilitate a complete simulation study workflow, from model import to experiment generation and execution.

### **Simulation Model Importer**
This source node is the entry point for integrating external simulation models into KNIME. A dedicated importer node exists for each supported tool: **AnyLogic Model Importer**, **SimPy Model Importer**, and **Simulation Model Importer (CMD-based)**.
- **Purpose**: Imports a simulation model file and prepares the KNIME environment for its execution.
- **Supported Tools**: AnyLogic (`.jar`), SimPy (`.py`), and Other (CMD-based, any file type).
- **Input/Output Options**:
    - **Input Type**: Selects whether the simulation requires an input file (`file-based`) or none (`none`). If file-based, the **Input Filename** specifies the file expected in the model's resource directory, and its resolved path is exported as `input_file_path`.
    - **Output Type**: Selects whether results are written to a file (`file-based`) or a connected database (`database`). If file-based, the **Output Filename** specifies the expected result file, and its resolved path is exported as `output_file_path`.
- **Functionality**:
    - Creates a timestamped `Resources` folder within the KNIME workspace to store a copy of the model, ensuring workflow portability.
    - Sets flow variables (`simulation_tool`, `resource_folder`, `model_path`, `output_mode`, and tool-specific variables) that are used by downstream nodes.
    - For SimPy models that use `argparse`, it automatically runs the script with `--help` to discover model parameters and their default values, exposing them as a table output.
    - For CMD-based tools, stores the user-defined command (including `{model_path}` placeholder support) as a flow variable for use by the Executor.
- **Output**: A custom `SimulationModelPort` containing a reference to the model in the workspace and an optional table with default arguments for SimPy models.

### **Factor Definition (DoE)**
This node allows you to define the factors and their corresponding levels (values) for your experiments.
- **Purpose**: Generates a definition of possible values for one or more experimental factors.
- **Modes**:
    - **Table-based**: Defines multiple factors at once using metadata from an input table. Each unique value in the selected identifier column results in one factor column in the output. Requires specifying the table name, identifier column, and value column.
    - **Argument-based**: Defines a single standalone factor directly via the node's configuration dialog, without requiring an input table. Useful for factors that are not part of a simulation database schema.
- **Data Types**: Supports both `String` (for categorical levels, encoded numerically and stored as a flow variable mapping) and `Numeric` (for ranges defined by a minimum, maximum, and step size) factors.
- **Output**: A table where each column represents a single factor, and the rows contain its possible values. This table serves as an input for the `Design of Experiments` node.

### **Design of Experiments**
This node takes factor definitions and generates a structured experimental plan.
- **Purpose**: Combines factor definitions to create a set of experiment configurations based on a selected DoE strategy.
- **Supported Methods**:
    - **Full Factorial**: Generates all possible combinations of factor levels.
    - **Latin Hypercube Sampling (LHS)**: Space-filling random sampling across factor ranges.
    - **Space-Filling LHS**: Enhanced LHS that maximizes distances between points via the maximin criterion.
    - **Plackett-Burman**: Efficient screening design requiring exactly two levels per factor.
- **Functionality**:
    - Merges inputs from multiple `Factor Definition` nodes.
    - Includes a safeguard to prevent combinatorial explosion with Full Factorial designs (throws an error for >1,000,000 runs).
    - Automatically reverses numeric encodings for string-type factors back to their original labels using flow variable mappings.
- **Outputs**:
    - **Wide-Format Table**: The primary output, where each row is a unique experiment configuration and each column is a factor.
    - **Long-Format Table**: A tidy-data version of the design, where each row corresponds to a single factor setting within a configuration. Useful for certain types of analysis, reporting, and table-based simulation input formats.

### **Simulation Model Executor**
This sink node executes the simulation model for each experimental configuration. A dedicated executor node exists for each supported tool: **AnyLogic Model Executor**, **SimPy Model Executor**, and **Simulation Model Executor (CMD-based)**.
- **Purpose**: Runs the imported simulation model using the configuration provided by the input table.
- **Inputs**:
    - The `SimulationModelPort` from the `Importer` node.
    - A configuration table (typically the wide-format output from the `Design of Experiments` node).
- **Supported Tools**:
    - **AnyLogic**: Launches the model via a platform-specific script (`.bat` / `.sh`) found in the resource folder and relocates output files to a timestamped results directory.
    - **SimPy**: Runs the Python script with command-line arguments derived from the input table columns, using the `output_file_cmd` flow variable to redirect the `--output` argument.
    - **Other (CMD-based)**: Executes the user-defined CMD command from the `cmd_command` flow variable, replacing the `{model_path}` placeholder with the resolved model path.
- **Functionality**:
    - Reads the `simulation_tool` flow variable to determine which simulation engine to invoke.
    - For AnyLogic and SimPy, updates the `output_file_path` flow variable to point to the relocated result file after execution. For Other (CMD-based), `output_file_path` retains the location set by the Importer.

## Flow Variables

The following flow variables are set by the **Simulation Model Importer** and consumed by the **Executor** and other downstream nodes:

| Variable | Set by | Description |
|---|---|---|
| `simulation_tool` | Importer | Name of the selected simulation tool (e.g., `ANYLOGIC`, `SIMPY`, `OTHER`) |
| `model_path` | Importer | Absolute path to the model file within the `Resources` folder |
| `resource_folder` | Importer | Absolute path to the timestamped `Resources` subdirectory |
| `workflow_folder_dir` | Importer | Absolute path to the root KNIME workspace folder |
| `input_file_path` | Importer | Absolute path to the input file within the `Resources` folder (Input Type `file-based` only) |
| `output_mode` | Importer | Selected output type (`FILEBASED` or `DATABASE`) |
| `output_file_path` | Importer, updated by Executor | Absolute path to the (expected, then actual) simulation result file (Output Type `file-based` only) |
| `output_file_cmd` | Importer | `--output <filename>` argument string for SimPy execution (file-based mode only) |
| `cmd_command` | Importer | CMD command for execution (Other tool only) |
| `simpy_help_output` | Importer | JSON string of parsed SimPy arguments and their defaults |
| `factor-mapping_<col>` | Factor Definition | JSON mapping of numeric indices to original string labels per factor |

## Requirements

The extension requires **KNIME Analytics Platform 5.x** with the Python extension configured.

If you install the extension as a bundled package (via the KNIME Community Hub or Extension Manager, see below), it ships with its own Python environment and **no additional setup is required** — all dependencies below are included automatically.

For **local development** (running the extension from source), the dependencies are managed via [`pixi.toml`](pixi.toml) and installed with:

```bash
pixi install
```

This provides, on top of `knime-extension` / `knime-python-base` (which already include `pandas` and `numpy` for table handling):

| Package | Purpose |
|---|---|
| `pyDOE3` | DoE algorithms (Full Factorial, LHS, Space-Filling LHS, Plackett-Burman) |
| `scipy` | Required by `pyDOE3` for sampling/distance calculations |
| `simpy` | Bundled so SimPy-based simulation models can be executed without a separate installation |

## Installation
### KNIME Analytics Platform

The extension can be installed from the KNIME Hub or via the KNIME Extension Manager.

#### Install from KNIME Hub
Drag and drop the following link into a running KNIME Analytics Platform instance:

> Install Simulation Study Extension from KNIME Community Hub *(<- TODO: Replace with actual Hub link)*

#### Install from Extension Manager
1. In KNIME, go to `File` → `Install extensions...`.
2. In the search box, type "Simulation Study".
3. Select the "Simulation Study Extension" and click `Next` to complete the installation.
4. Restart KNIME Analytics Platform.

## Usage

A typical simulation study workflow using this extension follows these steps:

1. **Import Model**: Start by adding the **Simulation Model Importer** node to your workflow. Select your simulation tool and provide the path to your model file. For CMD-based tools, also enter the command to execute it (e.g., `mytool run {model_path}`).
2. **Define Factors**: For each parameter you want to vary, add a **Factor Definition (DoE)** node. Configure each node to define the levels for that factor — either from table metadata or manually as arguments.
3. **Generate Design**: Connect the output(s) of the `Factor Definition` node(s) to the **Design of Experiments** node. Choose your desired experimental design method (e.g., Full Factorial or LHS) to generate the complete set of configurations.
4. **Execute Simulation**: Connect the `SimulationModelPort` from the `Importer` and the `Wide-Format DoE Table` from the `Design of Experiments` node to the **Simulation Model Executor** node. The node will trigger the simulation run for the provided configuration.
5. **Analyze Results**: After execution, the results can be read from the path provided by the `output_file_path` flow variable and analyzed using standard KNIME nodes for data processing, visualization, and statistics.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
