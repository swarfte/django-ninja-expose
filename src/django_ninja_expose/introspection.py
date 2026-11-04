"""Thin wrappers around ``Model._meta``."""

from __future__ import annotations

from django.db import models
from django.db.models import Model
from django.db.models.fields import AutoFieldMixin


def get_eligible_fields(model: type[Model]) -> dict[str, models.Field]:
    """Concrete fields plus forward many-to-many fields, keyed by name."""
    meta = model._meta
    result: dict[str, models.Field] = {f.name: f for f in meta.concrete_fields}
    result.update({f.name: f for f in meta.many_to_many})
    return result


def get_pk(model: type[Model]) -> models.Field:
    return model._meta.pk


def is_auto_pk(field: models.Field) -> bool:
    return isinstance(field, AutoFieldMixin)


def is_writable(field: models.Field) -> bool:
    """Whether a field may appear in create/update payloads."""
    return bool(field.editable) and not is_auto_pk(field)
