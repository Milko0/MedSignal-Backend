"""Domain exceptions -> HTTP codes."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain import exceptions as ex


def register_error_handlers(app: FastAPI) -> None:
    def mk(status: int):
        async def handler(_: Request, exc: Exception):
            return JSONResponse(status_code=status, content={"detail": str(exc)})
        return handler

    app.add_exception_handler(ex.NotFoundError, mk(404))
    app.add_exception_handler(ex.ConflictError, mk(409))
    app.add_exception_handler(ex.ValidationFailedError, mk(422))
    app.add_exception_handler(ex.AuthenticationError, mk(401))
    app.add_exception_handler(ex.PermissionDeniedError, mk(403))
    app.add_exception_handler(NotImplementedError, mk(501))
