"""Incremental update of labels and recalls. (FR-20)."""


class UpdateLabelsRecalls:
    """Incremental update of labels and recalls.

    Requirements: FR-20
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("UpdateLabelsRecalls")
