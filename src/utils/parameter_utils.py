import knime.extension as knext

# defines the supported simulation tools that can be integrated with the workflow
class SimTools(knext.EnumParameterOptions):
    ANYLOGIC = (
        "AnyLogic", 
        "Commercial simulation software for agent-based, discrete-event, and system dynamics modeling"
    )

    ASAP = (
        "AutoSched AP", 
        "Advanced Planning and Scheduling tool commonly used in semiconductor and manufacturing simulations"
    )

    SIMPY = (
        "SimPy", 
        "Open-source process-based discrete-event simulation framework in Python"
    )

# defines the output format options for the simulation
class SimulationOutputType(knext.EnumParameterOptions):
    FILEBASED = (
        "file-based", 
        "Outputs are saved as physical files in the local directory"
    )

    DATABASE = (
        "database", 
        "Outputs are sent directly to a connected database"
    )

# defines the structure in which factor inputs are provided to the simulation
class FactorInputType(knext.EnumParameterOptions):
    TABLEBASED = (
        "table-based", 
        "Factors are passed using KNIME tables, typically structured with metadata per row"
    )

    ARGUMENTBASED = (
        "argument-based", 
        "Factors are passed as direct function or command-line arguments to the simulator"
    )

# defines the type of values a factor can hold
class FactorDataType(knext.EnumParameterOptions):
    STRING = (
        "String", 
        "Factor values are categorical labels or symbolic states (e.g., 'Low', 'Medium', 'High')"
    )

    NUMERIC = (
        "Numeric", 
        "Factor values are numeric and support continuous or discrete ranges"
    )

# define the available experimental design strategies for simulation studies
# each enum entry represents a specific design of experiments (DoE) method 
# used to generate structured or sampled configurations based on factor definitions
# the selected design determines how combinations of input factors are generated and tested
class ExperimentDesigns(knext.EnumParameterOptions):
    # generates all possible combinations of factor levels
    FULLFAC = (
        "Full Factorial", 
        "Creates a complete factorial design by combining every level of each factor"
    )

    # samples the factor space evenly by stratifying each dimension
    LHS = (
        "Latin Hypercube Sampling", 
        "Generates a space-filling design where each factor range is divided into equally probable intervals and sampled once"
    )

    # improves standard LHS by maximizing distance between points for better space coverage
    SPACEFILLINGLHS = (
        "Space-Filling Latin Hypercube", 
        "Enhances Latin Hypercube Sampling to distribute samples more uniformly across the entire factor space"
    )

    # highly efficient screening design that reduces the number of experiments while detecting main effects
    PLACKETTBURMAN = (
        "Plackett-Burman", 
        "Creates an efficient screening design to identify influential factors with a minimal number of runs"
    )
