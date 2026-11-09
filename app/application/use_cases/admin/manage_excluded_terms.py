"""Excluded reaction terms. (FR-26)."""


class ManageExcludedTerms:
    """Excluded reaction terms.

    Requirements: FR-26
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("ManageExcludedTerms")
