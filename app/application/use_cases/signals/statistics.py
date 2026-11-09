"""Age group, sex, country, seriousness over time. (FR-08)."""


class Statistics:
    """Age group, sex, country, seriousness over time.

    Requirements: FR-08
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("Statistics")
