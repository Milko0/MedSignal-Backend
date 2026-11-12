from fastapi import HTTPException


def not_implemented(detail: str = "Not implemented yet") -> None:
    """Placeholder for endpoints that are designed (Swagger) but not built yet."""
    raise HTTPException(status_code=501, detail=detail)
