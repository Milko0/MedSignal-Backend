"""CRUD on reports. (FR-22)."""


class CrudReports:
    """CRUD on reports.

    Requirements: FR-22
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("CrudReports")
