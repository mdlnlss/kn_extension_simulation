import knime.extension as knext

class SimulationModelSpec(knext.PortObjectSpec):
    def serialize(self) -> dict:
        # No additional spec data to serialize
        return {}

    @staticmethod
    def deserialize(data: dict) -> "SimulationModelSpec":
        # No additional spec data to deserialize
        return SimulationModelSpec()

class SimulationModelPort(knext.PortObject):
    def __init__(self, spec: SimulationModelSpec, path: str):
        super().__init__(spec)
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    def __repr__(self):
        return f"ModelPath({self._path})"

    def serialize(self) -> bytes:
        return self._path.encode("utf-8")

    @classmethod
    def deserialize(cls, spec: SimulationModelSpec, storage: bytes) -> "SimulationModelPort":
        path = storage.decode("utf-8")
        return cls(spec, path)

simulation_port_type = knext.port_type(name="Simulation Model Port", object_class=SimulationModelPort, spec_class=SimulationModelSpec)
