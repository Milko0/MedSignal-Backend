"""Delete account. (FR-14)."""


class DeleteProfile:
    """Delete account.

    Requirements: FR-14
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("DeleteProfile")
