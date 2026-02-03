# Simulation Study Extension for KNIME

[![KNIME Hub](https://img.shields.io/badge/KNIME%20Hub-View%20on%20Hub-blue?style=flat-square)](https://hub.knime.com/) <!-- TODO: Add Hub Link -->
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

This repository is the home of the Simulation Study Extension for KNIME Analytics Platform. The extension provides a set of nodes for Design of Experiments (DoE) and simulation model execution.

The extension is developed by [Madlene Leißau](https://de.linkedin.com/in/madlene-leissau) from the Research Group [Industry Analytics](www.industry-analytics.de) at the [University of Applied Sciences Zwickau](www.whz.de) and [KNIME](www.knime.com]) as part of a Proof of Concept (PoC). The goal of the collaboration is to develop KNIME Analytics Platform extensions and best-practice workflows to provide a consistent and compatible platform for simulation studies across disciplines and simulation tools.

## Nodes

This extension provides a suite of nodes to facilitate a complete simulation study workflow, from model import to experiment generation and execution.

### **Simulation Model Importer**
This source node is the entry point for integrating external simulation models into KNIME.
- **Purpose**: Imports a simulation model file and prepares the KNIME environment for its execution.
- **Supported Tools**: AnyLogic (`.jar`), AutoSched AP (`.xmdx`), and SimPy (`.py`).
- **Functionality**:
    - Creates a sandboxed `Resources` folder within the KNIME workspace to store a copy of the model, ensuring workflow portability.
    - Sets crucial flow variables (`simulation_tool`, `resource_folder`, `model_path`) that are used by downstream nodes.
    - For SimPy models that use `argparse`, it automatically runs the script with `--help` to discover model parameters and their default values, exposing them as a table output.
- **Output**: A custom `SimulationModelPort` containing a reference to the model in the workspace and an optional table with default arguments for SimPy models.

### **Factor Definition (DoE)**
This node allows you to define the factors and their corresponding levels (values) for your experiments.
- **Purpose**: Generates a definition of possible values for one or more experimental factors.
- **Modes**:
    - **Table-based**: Defines multiple factors at once using metadata from an input table.
    - **Argument-based**: Defines a single factor manually via the node's configuration dialog.
- **Data Types**: Supports both `String` (for categorical levels) and `Numeric` (for ranges defined by a minimum, maximum, and step size) factors.
- **Output**: A table where each column represents a single factor, and the rows contain its possible values. This table serves as an input for the `Design of Experiments` node.

### **Design of Experiments**
This node takes factor definitions and generates a structured experimental plan.
- **Purpose**: Combines factor definitions to create a set of experiment configurations based on a selected DoE strategy.
- **Supported Methods**:
    - Full Factorial
    - Latin Hypercube Sampling (LHS)
    - Space-Filling LHS (using a maximin criterion)
    - Plackett-Burman
- **Functionality**:
    - Merges inputs from multiple `Factor Definition` nodes.
    - Includes a safeguard to prevent combinatorial explosion with Full Factorial designs (throws an error for >1,000,000 runs).
- **Outputs**:
    - **Wide-Format Table**: The primary output, where each row is a unique experiment configuration and each column is a factor.
    - **Long-Format Table**: A tidy-data version of the design, where each row corresponds to a single factor setting within a configuration. This is useful for certain types of analysis and reporting.

### **Simulation Model Executor**
This sink node executes the simulation model for each experimental configuration.
- **Purpose**: Runs the imported simulation model for every row of an input configuration table.
- **Inputs**:
    - The `SimulationModelPort` from the `Importer` node.
    - A configuration table (typically the wide-format output from the `Design of Experiments` node).
- **Functionality**:
    - Reads the `simulation_tool` flow variable to determine which simulation engine to use.
    - Iterates through the configuration table, passing the factor values for each run to the simulation model.
    - Sets an `output_file_path` flow variable pointing to the simulation results.

## Installation
### KNIME Analytics Platform

The extension can be installed from the KNIME Hub or via the KNIME Extension Manager.

#### Install from KNIME Hub
Drag and drop the following link into a running KNIME Analytics Platform instance:

> Install Simulation Study Extension from KNIME Hub *(<- TODO: Replace with actual Hub link)*

#### Install from Extension Manager
1. In KNIME, go to `File` → `Install KNIME Extensions...`.
2. In the search box, type "Simulation Study".
3. Select the "Simulation Study Extension" and click `Next` to complete the installation.
4. Restart KNIME Analytics Platform.

## Usage

A typical simulation study workflow using this extension follows these steps:

1.  **Import Model**: Start by adding the **Simulation Model Importer** node to your workflow. Configure it by selecting your simulation tool (e.g., SimPy) and providing the path to your model file.
2.  **Define Factors**: For each parameter you want to vary in your experiment, add a **Factor Definition (DoE)** node. Configure each node to define the levels for that factor (e.g., a numeric range from 1 to 10 with a step of 1).
3.  **Generate Design**: Connect the output(s) of the `Factor Definition` node(s) to the **Design of Experiments** node. Choose your desired experimental design method (e.g., Full Factorial or LHS) to generate the complete set of runs.
4.  **Execute Simulation**: Connect the `SimulationModelPort` from the `Importer` and the `Wide-Format DoE Table` from the `Design of Experiments` node to the **Simulation Model Executor** node. This node will run your model for each configuration.
5.  **Analyze Results**: After execution, the results can be read from the path provided by the `output_file_path` flow variable and analyzed using standard KNIME nodes for data processing, visualization, and statistics.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
