from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain import exceptions as e

_STATUS = {
    e.NotFoundError: 404,
    e.AlreadyExistsError: 409,
    e.InvalidCredentialsError: 401,
    e.PermissionDeniedError: 403,
    e.ValidationRuleError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(e.MedSignalError)
    async def handle_domain_error(_: Request, exc: e.MedSignalError) -> JSONResponse:
        status = next((code for cls, code in _STATUS.items() if isinstance(exc, cls)), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc) or exc.__class__.__name__})
