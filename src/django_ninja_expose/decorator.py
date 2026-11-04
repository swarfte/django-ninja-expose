"""The public ``@expose()`` decorator."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

from django.db.models import Model

from . import registry
from .config import INHERIT, SUPPORTED_METHODS, ExposureConfig
from .exceptions import (
    ExposeConfigurationError,
    InvalidAuthError,
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
    auth: Any = INHERIT,
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

    return ExposureConfig(
        resolved_path, resolved_methods, resolved_fields, resolved_query, _check_auth(model, auth)
    )


def _check_auth(model: type[Model], auth: Any) -> Any:
    """Validate ``auth``; the library never implements auth, it only hands it to Ninja."""
    if auth is INHERIT or auth is None:
        return auth
    items = auth if isinstance(auth, (list, tuple)) else [auth]
    if not items or not all(callable(a) for a in items):
        raise InvalidAuthError(
            f"Invalid auth {auth!r} for {model.__name__}: use INHERIT, None, "
            "a Ninja auth (e.g. django_auth) or a callable / list of callables."
        )
    return auth


def expose(
    path: str | None = None,
    methods: Iterable[str] | None = None,
    fields: Iterable[str] | None = None,
    query: Iterable[str] | None = None,
    auth: Any = INHERIT,
):
    """Expose a Django model as a REST API.

    ``None`` means automatic, ``[]`` means none, a list means explicit restriction.
    ``auth`` is ``INHERIT`` (default: use the ``NinjaAPI``/router auth), ``None``
    (disable auth for this model) or any Ninja auth (``django_auth``, ``HttpBearer()``,
    a callable, or a list of them). The model class is returned unchanged.
    """

    def decorator(model: M) -> M:
        registry.register(model, _resolve(model, path, methods, fields, query, auth))
        return model

    return decorator
