"""Daily poll; store every status change. (FR-28)."""


class PollShortages:
    """Daily poll; store every status change.

    Requirements: FR-28
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("PollShortages")
