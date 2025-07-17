import knime.extension as knext

# define available simulation tools
class SimTools(knext.EnumParameterOptions):
    ANYLOGIC = ("AnyLogic", "...")
    ASAP = ("AutoSched AP", "...")
    SIMPY = ("SimPy", "...")

# define the available experimental design strategies for simulation studies
# each enum entry represents a specific design of experiments (DoE) method 
# used to generate structured or sampled configurations based on factor definitions
# the selected design determines how combinations of input factors are generated and tested
class ExperimentDesigns(knext.EnumParameterOptions):
    # generates all possible combinations of factor levels
    FULLFAC = ("Full Factorial", "Creates a complete factorial design by combining every level of each factor")

    # samples the factor space evenly by stratifying each dimension
    LHS = ("Latin Hypercube Sampling", "Generates a space-filling design where each factor range is divided into equally probable intervals and sampled once")

    # improves standard LHS by maximizing distance between points for better space coverage
    SPACEFILLINGLHS = ("Space-Filling Latin Hypercube", "Enhances Latin Hypercube Sampling to distribute samples more uniformly across the entire factor space")

    # generates random samples and applies k-means clustering to reduce them to representative configurations
    RANDOMKMEANS = ("Random k-Means", "Samples the factor space randomly and uses k-means clustering to identify representative configurations")

    # highly efficient screening design that reduces the number of experiments while detecting main effects
    PLACKETTBURMAN = ("Plackett-Burman", "Creates an efficient screening design to identify influential factors with a minimal number of runs")

    # uses a structured quasi-random grid for even distribution over the parameter space
    SUKHAREDGRID = ("Sukharev-Grid Hypercube", "Generates a quasi-random grid that fills the factor space with well-distributed sample points")
