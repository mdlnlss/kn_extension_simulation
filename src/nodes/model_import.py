import logging
import knime.extension as knext
import os
import platform
import pandas as pd
import shutil

# Setup logger
LOGGER = logging.getLogger(__name__)

# Define available simulation tools
class Tool(knext.EnumParameterOptions):
    ANYLOGIC = ("AnyLogic", "...")
    ASAP = ("AutoSched AP", "...")
    SIMPY = ("SimPy", "...")

# Define input modes
class InputMode(knext.EnumParameterOptions):
    DATABASE = ("Database", "...")
    FILE = ("File", "...")

# Define available DB dialects - todo
class DbDialect(knext.EnumParameterOptions):
    POSTGRESQL = ("PostgreSQL", "The popular open-source database management system from PostgreSQL.")
    MYSQL = ("MySQL", "A widely used relational database management system from MySQL.")
    #SQLITE = ("SQLite", "A lightweight, file-based SQL database that runs without a server.") # --- not tested yet
    #MSSQL = ("Microsoft SQL Server", "Microsoft's relational database management system SQL Server.") # --- not tested yet

# Define the KNIME node
@knext.node(
    name="Simulation Model Importer",
    node_type=knext.NodeType.SOURCE,
    icon_path="icons/model.png",
    category="/community/simulation"
)

@knext.output_table(name="Output Data", description="Result of simulation model setup.")

class ModelImporter:
    """Short one-line description of the node.
        This node enables structured integration of external simulation models into a KNIME workflow.
        It supports multiple simulation tools and abstracts the differences in model file structures and configuration options.

        ### Supported Tools:
        - **AnyLogic**: Import a `.jar`-based model with either database or file-based input.
        - **AutoSched AP**: Import a `.xmdx` model file including its associated model name.
        - **SimPy**: Import a `.py` simulation script with an optional output file path.

        ### Features:
        - Dynamically adapts visible settings based on the selected simulation tool.
        - Validates required paths and file types during configuration and execution.
        - Automatically prepares a standardized `Resources/` directory within the KNIME workspace.
        - Makes selected configuration values available as flow variables (e.g., DB host, port, dialect, etc.).
        - Provides tool-specific information in the node output.

        ### Output Table:
        The output is a single-row table containing key metadata about the imported model,
        including paths, tool type, and configuration details relevant to the selected tool.
    """

    # Tool selection
    tool_choice = knext.EnumParameter(
        label="Simulation Tool",
        description="Select the simulation tool you are using.",
        default_value=Tool.ANYLOGIC.name,
        enum=Tool,
        style=knext.EnumParameter.Style.DROPDOWN,
    )

    # AnyLogic model path input
    anylogic_model_path = knext.LocalPathParameter(
        label="Model Path", 
        description="Enter a path to the model.jar. The required syntax of the path depends on the chosen file system.",
        placeholder_text="my/path/model.jar"
    ).rule(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]), knext.Effect.SHOW)

    # Validation for AnyLogic model path
    @anylogic_model_path.validator
    def validate_al_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith("model.jar"):
            raise ValueError ("Invalid path: must end with 'model.jar'")

    # AnyLogic input mode (DB or File)
    anylogic_input = knext.EnumParameter(
        label="Model Input",
        description="...",
        default_value=InputMode.DATABASE.name,
        enum=InputMode,
        style=knext.EnumParameter.Style.VALUE_SWITCH,
    ).rule(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),  knext.Effect.SHOW)

    # Parameters for database input mode
    dialect_display = knext.EnumParameter(
        label="DB dialect",
        description="DB dialect (choose one of: PostgreSQL, ...)",
        default_value=DbDialect.POSTGRESQL.name,
        enum=DbDialect,
        style=knext.EnumParameter.Style.DROPDOWN,
    ).rule(knext.And(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),  knext.OneOf(anylogic_input, [InputMode.DATABASE.name])), knext.Effect.SHOW)

    host = knext.StringParameter(
        label="Host", 
        description="...", 
        default_value="localhost"
    ).rule(knext.And(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),knext.OneOf(anylogic_input, [InputMode.DATABASE.name])), knext.Effect.SHOW)

    port = knext.IntParameter(
        label="Port", 
        description="Port of the DB server", 
        default_value=5432, 
        min_value=1
    ).rule(knext.And(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),  knext.OneOf(anylogic_input, [InputMode.DATABASE.name])), knext.Effect.SHOW)

    schema = knext.StringParameter(
        label="Database schema", 
        description="The optional database schema name.", 
        default_value="public", 
    ).rule(knext.And(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),  knext.OneOf(anylogic_input, [InputMode.DATABASE.name])), knext.Effect.SHOW)

    database = knext.StringParameter(
        label="Database", 
        description="Database name", 
        default_value="your_database"
    ).rule(knext.And(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),  knext.OneOf(anylogic_input, [InputMode.DATABASE.name])), knext.Effect.SHOW)

    # Parameter for file-based input
    anylogic_file = knext.StringParameter(
        label="File Name",
        description="...",
        default_value="input.xlsx"
    ).rule(knext.And(knext.OneOf(tool_choice, [Tool.ANYLOGIC.name]),  knext.OneOf(anylogic_input, [InputMode.FILE.name])), knext.Effect.SHOW)

    # what else for anylogic?

    # ASAP tool model path
    asap_model_path = knext.LocalPathParameter(
        label="Model Path", 
        description="Enter a path to the model .xmdx file. The required syntax of the path depends on the chosen file system",
        placeholder_text="my/path/model.xmdx"
    ).rule(knext.OneOf(tool_choice, [Tool.ASAP.name]),  knext.Effect.SHOW)

    # Validation for ASAP model path
    @asap_model_path.validator
    def validate_asap_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith(".xmdx"):
            raise ValueError ("Invalid path: must end with '.xmdx'")

    # ASAP model name
    asap_model_name = knext.StringParameter(
        label="Model",
        description="Model name",
        default_value="your_model"
    ).rule(knext.OneOf(tool_choice, [Tool.ASAP.name]),  knext.Effect.SHOW)

    # what else for as ap?
        
    # SimPy model path
    simpy_model_path = knext.LocalPathParameter(
        label="Model Path", 
        description="Enter a path to the XXX. The required syntax of the path depends on the chosen file system",
        placeholder_text="my/path/model.py"
    ).rule(knext.OneOf(tool_choice, [Tool.SIMPY.name]),  knext.Effect.SHOW)


    # Validation for SimPy model path
    @simpy_model_path.validator
    def validate_simpy_model_path(path: str):
        # If path is empty, likely the field is hidden and unused
        if not path:
            return
        if not path.endswith(".py"):
            raise ValueError ("Invalid path: must end with '.py'")

    # Output file name for SimPy
    simpy_output = knext.StringParameter(
        label="Output file",
        description="File name",
        default_value="simpy_output.csv"
    ).rule(knext.OneOf(tool_choice, [Tool.SIMPY.name]), knext.Effect.SHOW)

    # what else for simpy?

    # Other
    # ...

    # Configuration-time logic
    def configure(self, configure_context):
        configure_context.set_warning("This is a warning during configuration")

    # Main execution logic
    def execute(self, exec_context):
        # Derive paths for resource and workspace directories
        workflow_data_dir = exec_context.get_workflow_data_area_dir()
        workspace_folder_dir = os.path.dirname(os.path.dirname(workflow_data_dir))
        exec_context.flow_variables["workflow_folder_dir"] = workspace_folder_dir

        # Prepare the resource folder
        created_folder_dir = os.path.join(workspace_folder_dir, "Resources")
        os.makedirs(created_folder_dir, exist_ok=True)
        exec_context.flow_variables["resource_folder"] = created_folder_dir
    
        model_path = ""

        # Handle tool-specific flow variable setup
        if self.tool_choice == Tool.ANYLOGIC.name:
            exec_context.flow_variables["model_path"] = self.anylogic_model_path
            model_path = self.anylogic_model_path

            if self.anylogic_input == InputMode.DATABASE.name:
                exec_context.flow_variables["db_dialect"] = self.dialect_display
                exec_context.flow_variables["db_host"] = self.host
                exec_context.flow_variables["db_port"] = self.port
                exec_context.flow_variables["db_schema"] = self.schema
                exec_context.flow_variables["db_name"] = self.database

                if self.dialect_display == DbDialect.POSTGRESQL.name:
                    exec_context.flow_variables["db_url"] = f"jdbc:postgresql://{self.host}:{self.port}/{self.database}"
                elif self.dialect_display == DbDialect.MYSQL.name:
                    exec_context.flow_variables["db_url"] = f"jdbc:mysql://{self.host}:{self.port}/{self.database}"
                #elif self.dialect_display == DbDialect.SQLITE.name:
                #    exec_context.flow_variables["db_url"] = f"jdbc:sqlite:{self.database}" # --- not tested yet
                #elif self.dialect_display == DbDialect.MSSQL.name:
                #    exec_context.flow_variables["db_url"] = f"jdbc:sqlserver://{self.host}:{self.port};databaseName={self.database}" # --- not tested yet
                else:
                    raise knext.InvalidParametersError(f"Unknown dialect: {self.dialect_display}")

            elif self.anylogic_input == InputMode.FILE.name:
                exec_context.flow_variables["input_file"] = os.path.join(os.path.dirname(model_path), self.anylogic_file)

        elif self.tool_choice == Tool.ASAP.name:
            exec_context.flow_variables["model_path"] = self.asap_model_path
            model_path = self.asap_model_path
        elif self.tool_choice == Tool.SIMPY.name:
            exec_context.flow_variables["model_path"] = self.simpy_model_path
            model_path = self.simpy_model_path

        # OS and tool metadata as flow variables
        exec_context.flow_variables["os_name"] = platform.system()

        if platform.system() == "Windows":
            exec_context.flow_variables["os_slash"] = "\\"
        else:
            exec_context.flow_variables["os_slash"] = "/"
            
        exec_context.flow_variables["simulation_tool_used"] = self.tool_choice

        # Copy model files to the resource folder
        if model_path:
            # Empty folder
            for filename in os.listdir(created_folder_dir):
                file_path = os.path.join(created_folder_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    LOGGER.error(f"Error deleting {file_path}: {e}")

            # Copy files from model path
            model_dir = os.path.dirname(model_path)

            for item in os.listdir(model_dir):
                src = os.path.join(model_dir, item)
                dst = os.path.join(created_folder_dir, item)
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                        LOGGER.warning(f"Copy folder: {src} -> {dst}")
                    elif os.path.isfile(src):
                        shutil.copy2(src, dst)
                        LOGGER.warning(f"Copy file: {src} -> {dst}")
                except Exception as e:
                    LOGGER.error(f"Error copying {src} to {dst}: {e}")

        # Validate model path exists before proceeding
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Output based on selected simulation tool
        if self.tool_choice == Tool.ANYLOGIC.name:
            output_data = {
                "Tool": ["AnyLogic"],
                "Model Path": [self.anylogic_model_path],
                "Input Type": [self.anylogic_input],
                "Resource Folder": [created_folder_dir],
            }

        elif self.tool_choice == Tool.ASAP.name:
            output_data = {
                "Tool": ["AutoSched AP"],
                "Model Path": [self.asap_model_path],
                "Model Name": [self.asap_model_name],
                "Resource Folder": [created_folder_dir],
            }

        elif self.tool_choice == Tool.SIMPY.name:
            output_data = {
                "Tool": ["SimPy"],
                "Model Path": [self.simpy_model_path],
                "Output File": [self.simpy_output],
                "Resource Folder": [created_folder_dir],
            }

        df = pd.DataFrame(output_data)
        return knext.Table.from_pandas(df)