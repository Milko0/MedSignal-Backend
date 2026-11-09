"""Filter signals by drug, reaction, quarter, min reports. (FR-04, FR-05)."""


class ListSignals:
    """Filter signals by drug, reaction, quarter, min reports.

    Requirements: FR-04, FR-05
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("ListSignals")
