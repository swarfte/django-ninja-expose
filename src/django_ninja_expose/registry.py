"""Lightweight Model -> ExposureConfig registry."""

from __future__ import annotations

from django.db.models import Model

from .config import ExposureConfig

_registry: dict[type[Model], ExposureConfig] = {}


def register(model: type[Model], config: ExposureConfig) -> None:
    _registry[model] = config


def get_registry() -> dict[type[Model], ExposureConfig]:
    return dict(_registry)


def clear() -> None:
    _registry.clear()
