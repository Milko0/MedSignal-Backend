"""Dismiss one or all alerts. (FR-18)."""


class DismissAlert:
    """Dismiss one or all alerts.

    Requirements: FR-18
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("DismissAlert")
