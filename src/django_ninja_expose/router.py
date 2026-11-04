"""Build a Ninja Router from the exposure registry."""

from __future__ import annotations

from django.db.models import Model
from ninja import Router

from .exceptions import ExposeConfigurationError
from .operations import register_operations
from .registry import get_registry
from .schemas import build_schemas


def build_router(models: list[type[Model]] | None = None) -> Router:
    """Create a Router with endpoints for every exposed model (or the given ones)."""
    registry = get_registry()
    if models is not None:
        registry = {m: registry[m] for m in models}

    seen: dict[str, type[Model]] = {}
    router = Router()
    for model, config in registry.items():
        if config.path in seen:
            raise ExposeConfigurationError(f"Duplicate expose path: '{config.path}'.")
        seen[config.path] = model
        register_operations(router, model, config, build_schemas(model, config))
    return router
