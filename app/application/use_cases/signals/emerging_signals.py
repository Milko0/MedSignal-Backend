"""Latest quarter vs baseline. (FR-06)."""


class EmergingSignals:
    """Latest quarter vs baseline.

    Requirements: FR-06
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("EmergingSignals")
