"""Follow a drug. (FR-15)."""


class FollowDrug:
    """Follow a drug.

    Requirements: FR-15
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("FollowDrug")
