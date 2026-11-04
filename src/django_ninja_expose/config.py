"""Exposure configuration."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_METHODS: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD")


@dataclass(frozen=True)
class ExposureConfig:
    """Fully resolved configuration (no ``None`` values) for one model."""

    path: str
    methods: tuple[str, ...]
    fields: tuple[str, ...]
    query: tuple[str, ...]
