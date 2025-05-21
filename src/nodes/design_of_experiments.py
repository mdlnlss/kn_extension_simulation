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


@knext.parameter_group(label="Dynamic Selection")
class FactorConfiguration:
    unique_identifier = knext.ColumnParameter(
        "Identifier",
        "Select the column with your factor's unique identifier",
        port_index=0
    )

    factor_name = knext.ColumnParameter(
        "Name",
        "Select the column with the factor name",
        port_index=0
    )

    factor_value = knext.ColumnParameter(
        "Value",
        "Select the column with the factor values",
        port_index=0
    )

    min_value = knext.IntParameter(
        "Minimum",
        "...",
        default_value=0
    )

    max_value = knext.IntParameter(
        "Maximum",
        "...",
        default_value=1
    )

    step_value = knext.IntParameter(
        "Step",
        "...",
        default_value=1
    )

# Define the KNIME node
@knext.node(
    name="Design of Experiments",
    node_type=knext.NodeType.MANIPULATOR,
    icon_path="icons/try.png",
    category="/simulation"
)

@knext.input_table(name="Input Data", description="...")
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

    # Factor Configuration
    factor_configuration = knext.ParameterArray(
        label="Factor Configuration",
        description="...",
        parameters=FactorConfiguration(),
        layout_direction=knext.LayoutDirection.HORIZONTAL,
        button_text="Add New Configuration",
        array_title="Factor Configuration",
    )


    # Configuration-time logic
    def configure(self, configure_context, input_schema_1):
        configure_context.set_warning("This is a warning during configuration")

        #return input_schema_1

    # Main execution logic
    def execute(self, exec_context, input_1):

        input_df = input_1.to_pandas()
        factor_dict = {}

        # Iterate trough factor_configuration
        for i, config in enumerate(self.factor_configuration):
            unique_col = config.unique_identifier
            name_col = config.factor_name
            value_col = config.factor_value

            name = f"{unique_col}/{name_col}:{value_col}"

            min_val = config.min_value
            max_val = config.max_value
            step_val = config.step_value

            combinations = (
                input_df[[unique_col, name_col]]
                .drop_duplicates()
                .dropna()
                .values
            )

            for unique_val, name_val in combinations:
                factor_name = f"{unique_val}/{name_val}:{value_col}"
                values = list(range(min_val, max_val + 1, step_val))
                factor_dict[factor_name] = values

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
                    unique_id, factor_info = col.split("/", 1)
                    factor_name, value_col = factor_info.split(":", 1)
                except ValueError:
                    # In case column name doesn't follow expected pattern
                    unique_id, factor_name, value_col = "?", "?", "?"

                rows.append({
                    "EXPERIMENT": experiment_name,
                    "CONFIGURATION": configuration,
                    #"TABLE": "toolgroups",
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