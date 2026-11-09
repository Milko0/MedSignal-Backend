"""Mongo change event -> recompute and overwrite Redis keys, create alerts. (FR-30)."""


class ProjectChangeEvent:
    """Mongo change event -> recompute and overwrite Redis keys, create alerts.

    Requirements: FR-30
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("ProjectChangeEvent")
