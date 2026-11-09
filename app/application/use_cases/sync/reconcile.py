"""Rebuild Redis counters/statuses from MongoDB. (FR-27)."""


class Reconcile:
    """Rebuild Redis counters/statuses from MongoDB.

    Requirements: FR-27
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("Reconcile")
