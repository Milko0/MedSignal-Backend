"""Full load from FAERS bulk files; normalise names, dedupe. (FR-19, FR-29)."""


class LoadFaersBulk:
    """Full load from FAERS bulk files; normalise names, dedupe.

    Requirements: FR-19, FR-29
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("LoadFaersBulk")
