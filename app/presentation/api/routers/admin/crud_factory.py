"""Builds the four CRUD routers of the admin area (FR-22 to FR-25): list, create, read, update, delete."""
from fastapi import APIRouter, Depends, status

from app.application.dtos.common import PageRequest
from app.presentation.api.dependencies import pagination
from app.presentation.api.responses import CONFLICT, NOT_FOUND


def make_crud_router(name: str, fr: str, uc_dep, item_model, create_model=None, update_model=None,
                     id_label: str = "id", notes: str = "") -> APIRouter:
    """item_model: what is returned; create_model / update_model: request bodies (default item_model)."""
    create_model = create_model or item_model
    update_model = update_model or item_model
    router = APIRouter(prefix=f"/{name}", tags=[f"Admin: {name}"])

    @router.get("", response_model=list[item_model], summary=f"List {name} ({fr})",
                description=f"Paginated with page / page_size. {notes}".strip())
    async def list_items(page: PageRequest = Depends(pagination), uc=Depends(uc_dep)):
        return await uc.list(page.skip, page.limit)

    @router.post("", response_model=item_model, status_code=status.HTTP_201_CREATED, responses=CONFLICT,
                 summary=f"Create ({fr})", description=f"409 if the {id_label} already exists.")
    async def create_item(body: create_model, uc=Depends(uc_dep)):
        return await uc.create(body)

    @router.get("/{item_id}", response_model=item_model, responses=NOT_FOUND, summary=f"Read ({fr})",
                description=f"`item_id` is the {id_label}.")
    async def read_item(item_id: str, uc=Depends(uc_dep)):
        return await uc.get(item_id)

    @router.put("/{item_id}", response_model=item_model, responses={**NOT_FOUND, **CONFLICT},
                summary=f"Update ({fr})", description=f"`item_id` is the {id_label}.")
    async def update_item(item_id: str, body: update_model, uc=Depends(uc_dep)):
        return await uc.update(item_id, body)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND,
                   summary=f"Delete ({fr})", description=f"`item_id` is the {id_label}.")
    async def delete_item(item_id: str, uc=Depends(uc_dep)):
        await uc.delete(item_id)

    return router
