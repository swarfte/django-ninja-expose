"""Convenience entry points for wiring exposed models into a NinjaAPI."""

from __future__ import annotations

from ninja import NinjaAPI, Router

from .router import build_router


def get_router() -> Router:
    """Router containing every ``@expose()``d model. Call after apps are loaded."""
    return build_router()


def mount(api: NinjaAPI, prefix: str = "") -> NinjaAPI:
    """Attach all exposed models to ``api``."""
    api.add_router(prefix, get_router())
    return api
