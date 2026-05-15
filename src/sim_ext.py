import knime.extension as knext

main_category = knext.category(
    path="/community",
    level_id="simulation",
    name="Simulation Study Extension",
    description="Python Nodes for Simulation Studies",
    icon="icons/simulation.png",
)

from nodes import factor_range_doe
from nodes import design_of_experiments
from nodes import anylogic_model_import
from nodes import simpy_model_import
from nodes import other_model_import
from nodes import anylogic_model_executor
from nodes import simpy_model_executor
from nodes import other_model_executor