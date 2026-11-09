"""Same ingredient/class, route and form, not in shortage. (FR-10)."""


class RecommendAlternatives:
    """Same ingredient/class, route and form, not in shortage.

    Requirements: FR-10
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("RecommendAlternatives")
