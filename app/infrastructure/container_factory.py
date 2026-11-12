"""Chooses the adapters at start-up (STORAGE_BACKEND)."""
import importlib
import os

from app.application.container import Container
from app.core.config import Settings


async def build_container(settings: Settings) -> Container:
    if settings.storage_backend == "memory":
        from app.infrastructure.memory.factory import (
            build_loaded_container,
            build_memory_container,
        )
        if os.path.isdir(settings.data_dir):
            return await build_loaded_container(settings.data_dir)
        return build_memory_container()
    if settings.storage_backend == "databases":
        # Written by the team: it must return a Container whose fields are the MongoDB and Redis adapters.
        try:
            module = importlib.import_module("app.infrastructure.database_container")
        except ModuleNotFoundError as exc:
            raise RuntimeError("STORAGE_BACKEND=databases needs app/infrastructure/database_container.py "
                               "with build_database_container(settings)") from exc
        return await module.build_database_container(settings)
    raise RuntimeError(f"Unknown STORAGE_BACKEND: {settings.storage_backend}")
