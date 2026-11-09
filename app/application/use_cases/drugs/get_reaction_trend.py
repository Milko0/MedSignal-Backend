"""Monthly trend of top reactions. (FR-03)."""


class GetReactionTrend:
    """Monthly trend of top reactions.

    Requirements: FR-03
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("GetReactionTrend")
