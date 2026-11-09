"""Reported reactions not found in the label. (FR-07)."""


class GetLabelGaps:
    """Reported reactions not found in the label.

    Requirements: FR-07
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("GetLabelGaps")
