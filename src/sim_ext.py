import knime.extension as knext

main_category = knext.category(
    path="/community/simulation",
    level_id="sim",
    name="Simulation Studies",
    description="Python Nodes for Simulation Studies",
    icon="icons/icon.png",
)

from nodes import model_import
from nodes import design_of_experiments