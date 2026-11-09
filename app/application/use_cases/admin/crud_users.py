"""CRUD on users. (FR-25)."""


class CrudUsers:
    """CRUD on users.

    Requirements: FR-25
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("CrudUsers")
