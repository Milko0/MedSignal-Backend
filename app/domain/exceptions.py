class MedSignalError(Exception):
    """Base class of domain errors. The presentation layer maps them to HTTP codes."""


class NotFoundError(MedSignalError):
    pass


class AlreadyExistsError(MedSignalError):
    pass


class InvalidCredentialsError(MedSignalError):
    pass


class PermissionDeniedError(MedSignalError):
    pass


class ValidationRuleError(MedSignalError):
    pass


class TransformError(MedSignalError):
    """A raw source record cannot be turned into a clean model (the record is skipped and counted)."""
