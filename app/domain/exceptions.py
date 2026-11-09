"""Domain exceptions. Mapped to HTTP codes in presentation/api/error_handlers.py."""


class MedSignalError(Exception):
    """Base class."""


class NotFoundError(MedSignalError):
    pass


class ConflictError(MedSignalError):
    pass


class ValidationFailedError(MedSignalError):
    pass


class AuthenticationError(MedSignalError):
    pass


class PermissionDeniedError(MedSignalError):
    pass
