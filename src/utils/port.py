import knime.extension as knext

# defines the metadata specification for the custom Simulation Model Port
class SimulationModelSpec(knext.PortObjectSpec):
    def serialize(self) -> dict:
        # no additional metadata needs to be serialized for this port type
        return {}

    @staticmethod
    def deserialize(data: dict) -> "SimulationModelSpec":
        # simply return a new instance since there is no serialized spec data
        return SimulationModelSpec()

# defines the actual Simulation Model Port which holds a file path to a simulation model
class SimulationModelPort(knext.PortObject):
    def __init__(self, spec: SimulationModelSpec, path: str):
        # initialize the KNIME PortObject with its specification
        super().__init__(spec)  

        # store the path to the simulation model
        self._path = path  

    @property
    def path(self) -> str:
        # exposes the model path as a read-only property
        return self._path

    def __repr__(self):
        # used when printing or logging the object for easier debugging
        return f"ModelPath({self._path})"

    def serialize(self) -> bytes:
        # convert the model path to bytes so it can be stored by KNIME
        return self._path.encode("utf-8")

    @classmethod
    def deserialize(cls, spec: SimulationModelSpec, storage: bytes) -> "SimulationModelPort":
        # reconstruct the SimulationModelPort by decoding the stored path
        path = storage.decode("utf-8")
        return cls(spec, path)

# defines the KNIME port type for Simulation Models using the custom classes above
# name shown in the KNIME UI → class representing the actual data → class representing the port's metadata
simulation_port_type = knext.port_type(
    name="Simulation Model Port",                
    object_class=SimulationModelPort,
    spec_class=SimulationModelSpec
)
