"""The public ``@expose()`` decorator."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from django.db.models import Model

from . import registry
from .config import SUPPORTED_METHODS, ExposureConfig
from .exceptions import (
    ExposeConfigurationError,
    InvalidFieldError,
    InvalidQueryFieldError,
    UnsupportedMethodError,
)
from .introspection import get_eligible_fields

M = TypeVar("M", bound=type[Model])


def _resolve(
    model: type[Model],
    path: str | None,
    methods: Iterable[str] | None,
    fields: Iterable[str] | None,
    query: Iterable[str] | None,
) -> ExposureConfig:
    if path is not None and (not isinstance(path, str) or not path.strip("/")):
        raise ExposeConfigurationError(f"Invalid path {path!r} for {model.__name__}.")
    resolved_path = path.strip("/") if path is not None else model.__name__

    if methods is None:
        resolved_methods = SUPPORTED_METHODS
    else:
        seen: list[str] = []
        for m in methods:
            upper = str(m).upper()
            if upper not in SUPPORTED_METHODS:
                raise UnsupportedMethodError(f"{m} is not a supported HTTP method.")
            if upper not in seen:
                seen.append(upper)
        resolved_methods = tuple(seen)

    eligible = get_eligible_fields(model)
    if fields is None:
        resolved_fields = tuple(eligible)
    else:
        resolved_fields = tuple(dict.fromkeys(fields))
        for name in resolved_fields:
            if name not in eligible:
                raise InvalidFieldError(f"{model.__name__} has no field named '{name}'.")

    if query is None:
        resolved_query = resolved_fields
    else:
        resolved_query = tuple(dict.fromkeys(query))
        for name in resolved_query:
            if name not in eligible:
                raise InvalidQueryFieldError(
                    f"{model.__name__} has no field named '{name}' (used in query)."
                )
            if name not in resolved_fields:
                raise InvalidQueryFieldError(
                    f"Query field '{name}' of {model.__name__} is not in the exposed fields."
                )

    return ExposureConfig(resolved_path, resolved_methods, resolved_fields, resolved_query)


def expose(
    path: str | None = None,
    methods: Iterable[str] | None = None,
    fields: Iterable[str] | None = None,
    query: Iterable[str] | None = None,
):
    """Expose a Django model as a REST API.

    ``None`` means automatic, ``[]`` means none, a list means explicit restriction.
    The model class is returned unchanged.
    """

    def decorator(model: M) -> M:
        registry.register(model, _resolve(model, path, methods, fields, query))
        return model

    return decorator
