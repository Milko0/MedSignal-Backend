"""Builds the four CRUD routers of the admin area. Bodies are filled per resource as the repositories grow."""
from fastapi import APIRouter, status

from app.presentation.api.responses import not_implemented


def make_crud_router(name: str, fr: str) -> APIRouter:
    router = APIRouter(prefix=f"/{name}", tags=[f"Admin: {name}"])

    @router.get("", summary=f"List {name} ({fr})")
    async def list_items(skip: int = 0, limit: int = 50):
        not_implemented()

    @router.post("", status_code=status.HTTP_201_CREATED, summary=f"Create ({fr})")
    async def create_item(body: dict):
        not_implemented()

    @router.get("/{item_id}", summary=f"Read ({fr})")
    async def read_item(item_id: str):
        not_implemented()

    @router.put("/{item_id}", summary=f"Update ({fr})")
    async def update_item(item_id: str, body: dict):
        not_implemented()

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary=f"Delete ({fr})")
    async def delete_item(item_id: str):
        not_implemented()

    return router
