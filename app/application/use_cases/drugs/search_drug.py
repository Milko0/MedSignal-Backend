"""Typo-tolerant search, normalised to RxCUI. (FR-01)."""


class SearchDrug:
    """Typo-tolerant search, normalised to RxCUI.

    Requirements: FR-01
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("SearchDrug")
