"""Guest registers (username, email, password). (FR-11)."""


class Register:
    """Guest registers (username, email, password).

    Requirements: FR-11
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("Register")
