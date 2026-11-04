"""Schema factory: Read / Create / Update / Patch schemas built on Ninja."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db.models import Model
from ninja import Schema
from ninja.orm import create_schema
from ninja.orm.fields import get_schema_field
from pydantic import ConfigDict, create_model

from .config import ExposureConfig
from .introspection import get_eligible_fields, get_pk, is_writable


class _InputSchema(Schema):
    """Accept both `project` and the alias `project_id` for foreign keys."""

    model_config = ConfigDict(populate_by_name=True)


@dataclass(frozen=True)
class ModelSchemas:
    read: type[Schema]
    create: type[Schema]
    update: type[Schema]
    patch: type[Schema]
    pk_type: Any


def _build(
    model: type[Model],
    name: str,
    fields: list[str],
    optional: list[str] | str | None = None,
    base=Schema,
):
    if not fields:  # ninja treats an empty list as "all fields"
        return create_model(name, __base__=base)
    return create_schema(
        model,
        name=name,
        fields=fields,
        optional_fields=optional,
        base_class=base,
    )


def build_schemas(model: type[Model], config: ExposureConfig) -> ModelSchemas:
    eligible = get_eligible_fields(model)
    pk = get_pk(model)
    base = f"{model._meta.app_label.title()}{model.__name__}"

    read_fields = list(config.fields)

    create_fields = [n for n in read_fields if is_writable(eligible[n])]
    update_fields = [n for n in create_fields if n != pk.name]
    # blank many-to-many fields may be omitted (Ninja would otherwise require them)
    blank_m2m = [n for n in create_fields if eligible[n].many_to_many and eligible[n].blank]

    return ModelSchemas(
        read=_build(model, f"{base}Read", read_fields),
        create=_build(model, f"{base}Create", create_fields, optional=blank_m2m, base=_InputSchema),
        update=_build(model, f"{base}Update", update_fields, optional=blank_m2m, base=_InputSchema),
        patch=_build(model, f"{base}Patch", update_fields, optional="__all__", base=_InputSchema),
        pk_type=get_schema_field(pk, optional=False)[0],
    )
