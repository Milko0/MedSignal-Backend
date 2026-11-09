"""Ingestion logs. (FR-21)."""


class ListIngestionRuns:
    """Ingestion logs.

    Requirements: FR-21
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("ListIngestionRuns")
