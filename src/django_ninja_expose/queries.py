"""Query engine: safely turn query parameters into ORM filters."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from django.core.exceptions import FieldError, ValidationError
from django.db import models
from django.db.models import Model, QuerySet

from .exceptions import InvalidLookupError
from .introspection import get_eligible_fields

LOOKUP_SEP = "__"
_BOOL = {"true": True, "false": False}
_MULTI = {"in", "range"}
_ORM_ERRORS = (FieldError, ValueError, TypeError, ValidationError)


def _convert(raw: str, last: str, is_bool_field: bool) -> Any:
    lowered = raw.lower()
    if last == "isnull":
        if lowered not in _BOOL:
            raise InvalidLookupError("isnull expects 'true' or 'false'.")
        return _BOOL[lowered]
    if last in _MULTI:
        return raw.split(",")
    if is_bool_field and lowered in _BOOL:
        return _BOOL[lowered]
    return raw


def build_filters(
    model: type[Model],
    allowed: Iterable[str],
    params: Mapping[str, str],
    reserved: Iterable[str] = (),
) -> dict[str, Any]:
    """Validate params against the whitelist and return ``filter(**kwargs)``."""
    allowed = set(allowed)
    reserved = set(reserved)
    eligible = get_eligible_fields(model)
    filters: dict[str, Any] = {}

    for key, raw in params.items():
        if key in reserved:
            continue
        base, *rest = key.split(LOOKUP_SEP)
        if base not in allowed or base not in eligible:
            raise InvalidLookupError(f"Filtering by '{base}' is not allowed.")
        field = eligible[base]

        if rest:
            # The part directly after the field must be a lookup or transform of
            # the field itself; this blocks relationship traversal (project__name).
            first = rest[0]
            if not (field.get_lookup(first) or field.get_transform(first)):
                raise InvalidLookupError(f"Unsupported lookup '{first}' for field '{base}'.")
        is_bool = isinstance(field, models.BooleanField) and not rest
        filters[key] = _convert(raw, rest[-1] if rest else "exact", is_bool)

    # Let Django validate the full expression (transform chains, value coercion).
    try:
        model._default_manager.none().filter(**filters)
    except _ORM_ERRORS as exc:
        raise InvalidLookupError(f"Invalid filter: {exc}") from exc
    return filters


def apply_filters(qs: QuerySet, filters: dict[str, Any]) -> QuerySet:
    try:
        return qs.filter(**filters)
    except _ORM_ERRORS as exc:
        raise InvalidLookupError(f"Invalid filter: {exc}") from exc
