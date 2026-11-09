"""Generates the five CRUD routes for an admin resource (FR-22 to FR-25). Bodies are plain dicts in the skeleton."""
from fastapi import APIRouter

from app.presentation.api.responses import not_implemented


def crud_router(resource: str, fr: str) -> APIRouter:
    router = APIRouter(prefix=f"/{resource}", tags=[f"Admin - {resource}"])

    @router.get("", summary=f"List {resource} ({fr})")
    async def list_items(page: int = 1, page_size: int = 20):
        not_implemented(f"list {resource}")

    @router.post("", status_code=201, summary=f"Create ({fr})")
    async def create_item(body: dict):
        not_implemented(f"create {resource}")

    @router.get("/{item_id}", summary=f"Read ({fr})")
    async def read_item(item_id: str):
        not_implemented(f"read {resource}")

    @router.put("/{item_id}", summary=f"Update ({fr})")
    async def update_item(item_id: str, body: dict):
        not_implemented(f"update {resource}")

    @router.delete("/{item_id}", status_code=204, summary=f"Delete ({fr})")
    async def delete_item(item_id: str):
        not_implemented(f"delete {resource}")

    return router
