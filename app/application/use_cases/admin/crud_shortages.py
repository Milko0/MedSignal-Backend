"""CRUD on shortages. (FR-24)."""


class CrudShortages:
    """CRUD on shortages.

    Requirements: FR-24
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("CrudShortages")
