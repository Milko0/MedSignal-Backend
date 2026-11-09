"""Individual reports behind a signal. (FR-09)."""


class SignalReports:
    """Individual reports behind a signal.

    Requirements: FR-09
    Depends only on ports (application/ports) and the domain layer.
    """

    def __init__(self, **ports):  # TODO: replace with explicit port arguments
        self.ports = ports

    async def execute(self, *args, **kwargs):
        raise NotImplementedError("SignalReports")
