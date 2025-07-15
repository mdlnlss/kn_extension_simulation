import logging
import knime.extension as knext
import pandas as pd
from doepy import build
import time

# Setup logger
LOGGER = logging.getLogger(__name__)

# Define available simulation tools
class Design(knext.EnumParameterOptions):
    FULLFAC = ("Full Factorial", "...")
    LHS = ("Latin Hypercube Sampling", "...")
    SPACEFILLINGLHS = ("Space-Filling Latin Hypercube", "...")
    RANDOMKMEANS = ("Random k-Means", "...")
    PLACKETTBURMAN = ("Plackett-Burman", "...")
    SUKHAREDGRID = ("Sukharev-Grid Hypercube", "...")

# Define the KNIME node
@knext.node(
    name="Design of Experiments",
    node_type=knext.NodeType.MANIPULATOR,
    icon_path="icons/try.png",
    category="/community/simulation"
)

@knext.input_table(name="Input Data", description="...")
@knext.input_table(name="Input Data2", description="...", optional=True)
@knext.input_table(name="Input Data3", description="...", optional=True)
@knext.input_table(name="Input Data4", description="...", optional=True)
@knext.output_table(name="DoE Data", description="...")
@knext.output_table(name="Flattened DoE Table", description="...")

class DesignOfExperiments:
    """Short one-line description of the node.
        This node enables ...
    """
    # Design selection
    design_choice = knext.EnumParameter(
        label="Experiment Design",
        description="...",
        default_value=Design.FULLFAC.name,
        enum=Design,
        style=knext.EnumParameter.Style.DROPDOWN,
    )

    samples = knext.IntParameter(
        label="Number of Samples",
        description="...",
        default_value=50,
        min_value=1
    ).rule(
        knext.Or(
            knext.OneOf(design_choice, [Design.LHS.name]), 
            knext.OneOf(design_choice, [Design.SPACEFILLINGLHS.name]), 
            knext.OneOf(design_choice, [Design.RANDOMKMEANS.name]),
            knext.OneOf(design_choice, [Design.SUKHAREDGRID.name])
        ),
        knext.Effect.SHOW
    )

    # Configuration-time logic
    def configure(self, configure_context, input_schema_1, input_schema_2, input_schema_3, input_schema_4):
        configure_context.set_warning("This is a warning during configuration")

        #return input_schema_1

    # Main execution logic
    def execute(self, exec_context, input_1, input_2, input_3, input_4):

        try:
            input_df1 = input_1.to_pandas()
            dict1 = input_df1.to_dict(orient='list')
        except Exception:
            input_df1 = None
            dict1 = {}

        try:
            input_df2 = input_2.to_pandas()
            dict2 = input_df2.to_dict(orient='list')
        except Exception:
            input_df2 = None
            dict2 = {}

        merged = dict1 | dict2

        factor_dict = merged

        if self.design_choice == Design.FULLFAC.name:
            df_doe = build.full_fact(factor_dict)
        elif self.design_choice == Design.LHS.name:
            df_doe = build.lhs(factor_dict, num_samples=self.samples)
        elif self.design_choice == Design.SPACEFILLINGLHS.name:
            df_doe = build.space_filling_lhs(factor_dict, num_samples=self.samples)
        elif self.design_choice == Design.RANDOMKMEANS.name:
            df_doe = build.random_k_means(factor_dict, num_samples=self.samples)
        elif self.design_choice == Design.PLACKETTBURMAN.name:
            df_doe = build.plackett_burman(factor_dict)
        elif self.design_choice == Design.SUKHAREDGRID.name:
            df_doe = build.sukharev(factor_dict, num_samples=self.samples)
        else:
            raise ValueError(f"Design {self.design_choice} is not implemented.")
        
        df_doe.insert(
            0,
            "CONFIGURATION",
            [f"configuration_{i:06d}" for i in range(len(df_doe))]
        )

        # Prepare long-format output
        rows = []
        experiment_name = f"{time.strftime('%Y-%m-%d_%H%M%S')}_{self.design_choice}"

        # Iterate over rows and columns to flatten the DoE table
        for _, row in df_doe.iterrows():
            configuration = row["CONFIGURATION"]
            for col in df_doe.columns:
                if col == "CONFIGURATION":
                    continue  # skip CONFIGURATION column

                try:
                    parts = col.split(":")
                    
                    table = parts[0] if len(parts) > 0 else "?"
                    
                    label_map = {}
                    for part in parts[1:]:
                        if part.startswith("[") and "]" in part:
                            label = part[1:part.find("]")]
                            value = part[part.find("]")+1:]
                            label_map[label.upper()] = value
                        else:
                            value_col = part  # Der letzte Teil ohne Label
                    
                    unique_col = "AREA"
                    unique_id = label_map.get("AREA", "?")
                    name_col = "TOOLGROUP"
                    factor_name = label_map.get("TOOLGROUP", "?")
                    value_col = value_col if "value_col" in locals() else "?"
                    
                except Exception as e:
                    LOGGER.warning(f"Failed to parse column name '{col}': {e}")
                    table = unique_id = factor_name = value_col = unique_col = name_col = "?"

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

        # Create long-format dataframe
        df_long = pd.DataFrame(rows)

        return knext.Table.from_pandas(df_doe), knext.Table.from_pandas(df_long)