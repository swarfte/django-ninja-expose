"""Exposure configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ninja.constants import NOT_SET

SUPPORTED_METHODS: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD")

#: Default for ``auth``: use whatever the parent ``NinjaAPI`` / router defines.
#: This is Ninja's own "not set" sentinel, so it is handed to Ninja unchanged.
INHERIT: Any = NOT_SET


@dataclass(frozen=True)
class ExposureConfig:
    """Fully resolved configuration for one model.

    ``auth`` is ``INHERIT`` (use the API/router auth), ``None`` (no auth) or a
    Ninja-compatible auth callable / list of callables.
    """

    path: str
    methods: tuple[str, ...]
    fields: tuple[str, ...]
    query: tuple[str, ...]
    auth: Any = INHERIT
