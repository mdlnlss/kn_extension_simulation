import logging
import knime.extension as knext
import pandas as pd
from doepy import build
from utils import string_factor_mapping as str_map, parameter_definition as pdef
import time

# setup logger
LOGGER = logging.getLogger(__name__)

# define the KNIME node
@knext.node(
    name="Design of Experiments",
    node_type=knext.NodeType.MANIPULATOR,
    icon_path="icons/try.png",
    category="/community/simulation"
)

@knext.input_table(name="Input Data", description="...")
@knext.input_table(name="Input Data2", description="...", optional=True)
@knext.output_table(name="DoE Data", description="...")
@knext.output_table(name="Flattened DoE Table", description="...")

class DesignOfExperiments:
    """Short one-line description of the node.
        This node enables ...
    """
    # enum parameter to let the user select the design of experiments method
    # options are defined in the Design enum (e.g. FULLFAC, LHS, etc.)
    # displayed as a dropdown menu in the UI
    design_choice = knext.EnumParameter(
        label="Experiment Design",
        description="...",
        default_value=pdef.ExperimentDesigns.FULLFAC.name,
        enum=pdef.ExperimentDesigns,
        style=knext.EnumParameter.Style.DROPDOWN,
    )

    # integer parameter to define how many samples to generate in sampling-based designs
    # only shown when the selected design supports sampling
    samples = knext.IntParameter(
        label="Number of Samples",
        description="...",
        default_value=50,
        min_value=1
    ).rule(
        knext.Or(
            knext.OneOf(design_choice, [pdef.ExperimentDesigns.LHS.name]), 
            knext.OneOf(design_choice, [pdef.ExperimentDesigns.SPACEFILLINGLHS.name]), 
            knext.OneOf(design_choice, [pdef.ExperimentDesigns.RANDOMKMEANS.name]),
            knext.OneOf(design_choice, [pdef.ExperimentDesigns.SUKHAREDGRID.name])
        ),
        knext.Effect.SHOW
    )

    # configuration-time logic
    def configure(self, configure_context, input_schema_1, input_schema_2, input_schema_3, input_schema_4):
        configure_context.set_warning("This is a warning during configuration")

        #return input_schema_1

    # main execution logic
    def execute(self, exec_context, input_1, input_2, input_3, input_4):
        # collect all factor definitions from up to four input tables into one dictionary
        # each table is expected to contain key-value pairs defining a single or multiple factors
        merged_dict = {}

        # iterate over all input tables and merge their content
        for input_table in [input_1, input_2, input_3, input_4]:
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
        if self.design_choice == pdef.ExperimentDesigns.FULLFAC.name:
            df_doe = build.full_fact(factor_dict)
        elif self.design_choice == pdef.ExperimentDesigns.LHS.name:
            df_doe = build.lhs(factor_dict, num_samples=self.samples)
        elif self.design_choice == pdef.ExperimentDesigns.SPACEFILLINGLHS.name:
            df_doe = build.space_filling_lhs(factor_dict, num_samples=self.samples)
        elif self.design_choice == pdef.ExperimentDesigns.RANDOMKMEANS.name:
            df_doe = build.random_k_means(factor_dict, num_samples=self.samples)
        elif self.design_choice == pdef.ExperimentDesigns.PLACKETTBURMAN.name:
            df_doe = build.plackett_burman(factor_dict)
        elif self.design_choice == pdef.ExperimentDesigns.SUKHAREDGRID.name:
            df_doe = build.sukharev(factor_dict, num_samples=self.samples)
        else:
            raise ValueError(f"Design {self.design_choice} is not implemented.")
        
        # insert a unique configuration ID column to identify each row in the design
        # format: configuration_000001, configuration_000002, etc.
        df_doe.insert(
            0,
            "CONFIGURATION",
            [f"configuration_{i:06d}" for i in range(len(df_doe))]
        )

        # collect transformed rows in long format for later table output
        rows = []

        # generate a unique experiment name using timestamp and design type
        experiment_name = f"{time.strftime('%Y-%m-%d_%H%M%S')}_{self.design_choice}"

        # iterate over each configuration row to flatten the wide format into long format
        for _, row in df_doe.iterrows():
            configuration = row["CONFIGURATION"]
            for col in df_doe.columns:
                if col == "CONFIGURATION":
                    continue

                # parse metadata embedded in the column name
                try:
                    parts = col.split(":")
                    
                    # the first part should always be the table name
                    table = parts[0] if parts else "?"
                    
                    # holds extracted label-value pairs
                    label_map = {}
                    value_col = "?"

                    for part in parts[1:]:
                        if part.startswith("[") and "]" in part:
                            # extract the label inside [] and its value
                            label = part[1:part.find("]")]
                            value = part[part.find("]")+1:]
                            label_map[label.upper()] = value

                        else:
                            # assume the last part (not a label) is the actual value column name
                            value_col = part
                    
                    # resolve expected metadata from label_map or fallback to "?"
                    labels_sorted = sorted(label_map.items())
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

        # apply factor mappings (such as translation, normalization, or remapping) to each row
        # this depends on flow variables and a mapping utility defined elsewhere
        df_long = str_map.string_factor_mapping(df_long, exec_context.flow_variables, axis=1)
        
        # ensure that all values are strings, as KNIME ports expect uniform data types
        df_long["VALUES"] = df_long["VALUES"].astype(str)

        # return both the wide-format design table and the long-format expanded representation
        return knext.Table.from_pandas(df_doe), knext.Table.from_pandas(df_long)