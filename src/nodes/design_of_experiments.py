import logging
import knime.extension as knext
from utils import parameter_utils as parameters
from sim_ext import main_category
import pandas as pd
import time

# setup logger
LOGGER = logging.getLogger(__name__)

# define the KNIME node
@knext.node(
    name="Design of Experiments",
    node_type=knext.NodeType.MANIPULATOR,
    icon_path="icons/design of experiments.png",
    category=main_category
)

@knext.input_table_group(
    name="Input Data", 
    description="One or more input tables defining factor configurations"
)

@knext.output_table(
    name="DoE Data", 
    description="A table in wide format where each row represents one configuration and each column is a factor"
)

@knext.output_table(
    name="Flattened DoE Table", 
    description="A long-format table where each row represents a single factor-value assignment for a specific configuration"
)

class DesignOfExperiments:
    """Generates experimental designs based on input factor definitions

    This node combines one or more factor definition tables and applies a selected 
    experimental design strategy (e.g. full factorial, Latin hypercube, etc.) to 
    produce a structured set of experiment configurations. 
    Output is provided in both wide and long table formats.
    """

    # enum parameter to let the user select the design of experiments method
    # options are defined in the Design enum (e.g. FULLFAC, LHS, etc.)
    # displayed as a dropdown menu in the UI
    design_choice = knext.EnumParameter(
        label="Experiment Design",
        description="Select the method to generate the experiment design (e.g. full factorial, Latin hypercube sampling, etc.)",
        default_value=parameters.ExperimentDesigns.FULLFAC.name,
        enum=parameters.ExperimentDesigns,
        style=knext.EnumParameter.Style.DROPDOWN,
    )

    # integer parameter to define how many samples to generate in sampling-based designs
    # only shown when the selected design supports sampling
    samples = knext.IntParameter(
        label="Number of Samples",
        description="Specify how many samples to generate (only used for sampling-based designs like LHS or k-Means)",
        default_value=50,
        min_value=1
    ).rule(
        knext.Or(
            knext.OneOf(design_choice, [parameters.ExperimentDesigns.LHS.name]), 
            knext.OneOf(design_choice, [parameters.ExperimentDesigns.SPACEFILLINGLHS.name]), 
            knext.OneOf(design_choice, [parameters.ExperimentDesigns.RANDOMKMEANS.name]),
            knext.OneOf(design_choice, [parameters.ExperimentDesigns.SUKHAREDGRID.name])
        ),
        knext.Effect.SHOW
    )

    # configuration-time logic
    def configure(self, configure_context, input_table_specs: list[knext.Schema]):
        configure_context.set_warning("This is a warning during configuration")

        #return knext.Schema([], []), knext.Schema([], [])

    # main execution logic
    def execute(self, exec_context, input_tables: list[knext.Table]):
        from doepy import build
        from utils import factor_utils

        # collect all factor definitions from up to four input tables into one dictionary
        # each table is expected to contain key-value pairs defining a single or multiple factors
        merged_dict = {}

        # iterate over all input tables and merge their content
        for input_table in input_tables:
            if input_table is not None:
                try:
                    # convert KNIME table to pandas DataFrame
                    df = input_table.to_pandas()

                    # convert DataFrame to dictionary with lists as values, and merge with existing dictionary
                    merged_dict |= df.to_dict(orient='list')
                except Exception as e:
                    print(f"Fehler beim Verarbeiten eines Inputs: {e}")

        # the merged dictionary is treated as the full set of factor definitions
        factor_dict = merged_dict

        # generate the design of experiments based on the selected design strategy
        if self.design_choice == parameters.ExperimentDesigns.FULLFAC.name:
            df_doe = build.full_fact(factor_dict)
        elif self.design_choice == parameters.ExperimentDesigns.LHS.name:
            df_doe = build.lhs(factor_dict, num_samples=self.samples)
        elif self.design_choice == parameters.ExperimentDesigns.SPACEFILLINGLHS.name:
            df_doe = build.space_filling_lhs(factor_dict, num_samples=self.samples)
        elif self.design_choice == parameters.ExperimentDesigns.RANDOMKMEANS.name:
            df_doe = build.random_k_means(factor_dict, num_samples=self.samples)
        elif self.design_choice == parameters.ExperimentDesigns.PLACKETTBURMAN.name:
            df_doe = build.plackett_burman(factor_dict)
        elif self.design_choice == parameters.ExperimentDesigns.SUKHAREDGRID.name:
            df_doe = build.sukharev(factor_dict, num_samples=self.samples)
        else:
            raise ValueError(f"Design {self.design_choice} is not implemented.")
        
        # generate a unique experiment name using timestamp and design type
        experiment_name = f"{time.strftime('%Y-%m-%d_%H%M%S')}_{self.design_choice}"

        df_doe.insert(
            0,
            "EXPERIMENT",
            experiment_name
        )

        # insert a unique configuration ID column to identify each row in the design
        # format: configuration_000001, configuration_000002, etc.
        df_doe.insert(
            1,
            "CONFIGURATION",
            [f"configuration_{i:06d}" for i in range(len(df_doe))]
        )

        # collect transformed rows in long format for later table output
        rows = []

        # iterate over each configuration row to flatten the wide format into long format
        for _, row in df_doe.iterrows():
            configuration = row["CONFIGURATION"]
            for col in df_doe.columns:
                if col == "EXPERIMENT" or col == "CONFIGURATION":
                    continue

                # parse metadata embedded in the column name
                try:
                    # split the column name by ":" to extract metadata parts
                    parts = col.split(":")

                    # argument-based columns contain no metadata, only the raw column name
                    is_argument_based = len(parts) == 1  

                    if is_argument_based:
                        # handle case where no metadata is encoded in the column name
                        # typically used in argument-based factor configurations
                        table = "ARGUMENT"

                        # use the raw column name for all fields
                        unique_col = unique_id = name_col = value_col = factor_name = col  

                    else:
                        # table-based encoding expected in format: table:[KEY]value:[KEY]value:column
                        table = parts[0] if parts else "?"

                        # dictionary to store extracted metadata labels and values
                        label_map = {} 

                        # fallback in case no raw value column is found
                        value_col = "?"  

                        # loop over the remaining parts to extract metadata or determine the actual value column name
                        for part in parts[1:]:
                            if part.startswith("[") and "]" in part:
                                # parse key-value pair from format [KEY]value
                                label = part[1:part.find("]")]
                                value = part[part.find("]") + 1:]
                                label_map[label.upper()] = value
                            else:
                                # assume the last part (not enclosed in brackets) is the actual value column
                                value_col = part

                        # sort the label map entries alphabetically by key to assign unique_id and factor_name consistently
                        labels_sorted = sorted(label_map.items())

                        # extract metadata fields from sorted entries
                        unique_col, unique_id = labels_sorted[0] if labels_sorted else ("?", "?")
                        name_col, factor_name = labels_sorted[1] if len(labels_sorted) > 1 else ("?", "?")


                except Exception as e:
                    # fallback for malformed column names or unexpected parsing errors
                    LOGGER.warning(f"Failed to parse column name '{col}': {e}")
                    table = unique_id = factor_name = value_col = unique_col = name_col = "?"

                # append the parsed information and value to the long-format result
                rows.append({
                    "EXPERIMENT": experiment_name,
                    "CONFIGURATION": configuration,
                    "TABLE": table,
                    "COL_UNIQUEID": unique_col,
                    "COL_FACTOR": name_col,
                    "COL_VALUE": value_col,
                    "UNIQUE IDENTIFIER": unique_id,
                    "FACTOR": factor_name,
                    "VALUES": row[col]
                })

        # create a long-format DataFrame where each row represents a single factor assignment
        df_long = pd.DataFrame(rows)

        # apply factor mappings (such as translation, normalization, or remapping)
        # this depends on flow variables and a mapping utility defined elsewhere
        df_doe = factor_utils.doe_string_mapping(df_doe, exec_context.flow_variables, axis=0)
        df_long = factor_utils.doe_string_mapping(df_long, exec_context.flow_variables, axis=1)
        
        # ensure that all values are strings, as KNIME ports expect uniform data types
        df_long["VALUES"] = df_long["VALUES"].astype(str)

        if df_long["TABLE"].eq("ARGUMENT").all():
            keep_cols = ["EXPERIMENT", "CONFIGURATION", "FACTOR", "VALUES"]
            df_long = df_long[keep_cols]

        # return both the wide-format design table and the long-format expanded representation
        return knext.Table.from_pandas(df_doe), knext.Table.from_pandas(df_long)