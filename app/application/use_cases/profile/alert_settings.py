"""Read/save alert preferences (beyond the requirement list). (FR-17)."""


class AlertSettings:
    """Read/save alert preferences (beyond the requirement list).

    Requirements: FR-17
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("AlertSettings")
