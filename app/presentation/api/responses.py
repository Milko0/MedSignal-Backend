from typing import NoReturn

from fastapi import HTTPException


def not_implemented(what: str) -> NoReturn:
    raise HTTPException(status_code=501, detail=f"{what}: not implemented yet (skeleton)")
