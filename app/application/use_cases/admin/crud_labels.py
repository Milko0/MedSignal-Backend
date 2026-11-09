"""CRUD on labels. (FR-23)."""


class CrudLabels:
    """CRUD on labels.

    Requirements: FR-23
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("CrudLabels")
