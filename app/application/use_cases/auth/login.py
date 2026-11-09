"""Verify credentials and issue a JWT. (FR-12)."""


class Login:
    """Verify credentials and issue a JWT.

    Requirements: FR-12
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("Login")
