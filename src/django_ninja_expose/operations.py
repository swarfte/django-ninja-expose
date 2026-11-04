"""Operation factory: CRUD views registered on a Ninja router."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string
from ninja import Router, Status
from ninja.conf import settings as ninja_settings
from ninja.errors import HttpError
from ninja.errors import ValidationError as NinjaValidationError
from ninja.pagination import paginate

from .config import ExposureConfig
from .exceptions import InvalidLookupError
from .introspection import get_eligible_fields
from .queries import apply_filters, build_filters
from .schemas import ModelSchemas


def _reserved_params() -> set[str]:
    """Query params owned by the Ninja pagination class (limit/offset/page...)."""
    paginator = import_string(ninja_settings.PAGINATION_CLASS)
    return set(paginator.Input.model_fields)


def _validation_error(exc: ValidationError) -> NinjaValidationError:
    if hasattr(exc, "error_dict"):
        errors = [
            {"loc": ["body", k], "msg": "; ".join(v), "type": "value_error"}
            for k, v in exc.message_dict.items()
        ]
    else:
        errors = [{"loc": ["body"], "msg": "; ".join(exc.messages), "type": "value_error"}]
    return NinjaValidationError(errors)


def _resolve_field(model: type[Model], key: str) -> models.Field:
    try:
        return model._meta.get_field(key)
    except Exception:  # alias such as `project_id`
        return model._meta.get_field(key.removesuffix("_id"))


def _apply(model: type[Model], instance: Model, data: dict[str, Any]) -> dict[str, list]:
    """Assign payload data to instance; return m2m values to set after save."""
    m2m: dict[str, list] = {}
    for key, value in data.items():
        field = _resolve_field(model, key)
        if field.many_to_many:
            if value is None:  # omitted optional m2m: leave unchanged
                continue
            m2m[field.name] = list(value or [])
        elif field.is_relation:
            setattr(instance, field.attname, value)
        else:
            setattr(instance, field.name, value)
    return m2m


def _save(model: type[Model], instance: Model, data: dict[str, Any]) -> Model:
    try:
        with transaction.atomic():
            m2m = _apply(model, instance, data)
            # Validate only what the payload touched (relevant for PATCH).
            touched = {_resolve_field(model, k).name for k in data}
            exclude = [f.name for f in model._meta.fields if f.name not in touched]
            instance.full_clean(exclude=exclude)
            for name, ids in m2m.items():
                related = model._meta.get_field(name).remote_field.model
                if related._default_manager.filter(pk__in=ids).count() != len(set(ids)):
                    raise ValidationError({name: ["Some related objects do not exist."]})
            instance.save()
            for name, ids in m2m.items():
                getattr(instance, name).set(ids)
    except ValidationError as exc:
        raise _validation_error(exc) from exc
    return instance


def register_operations(
    router: Router, model: type[Model], config: ExposureConfig, schemas: ModelSchemas
) -> None:
    collection = f"/{config.path}"
    detail = f"/{config.path}/{{pk}}"
    prefix = model._meta.label_lower.replace(".", "_")
    methods = config.methods
    reserved = _reserved_params()
    Read, pk_type = schemas.read, schemas.pk_type

    def queryset() -> models.QuerySet:
        return model._default_manager.all()

    def filtered(request: HttpRequest) -> models.QuerySet:
        params = {k: request.GET[k] for k in request.GET}
        try:
            filters = build_filters(model, config.query, params, reserved)
            return apply_filters(queryset(), filters)
        except InvalidLookupError as exc:
            raise HttpError(400, str(exc)) from exc

    def add(url: str, http_method: str, func, name: str, **kwargs) -> None:
        func.__name__ = name
        router.add_api_operation(
            url,
            [http_method],
            func,
            operation_id=f"{prefix}_{name}",
            tags=[model.__name__],
            **kwargs,
        )

    if "GET" in methods:

        def list_view(request: HttpRequest, **kwargs):
            return filtered(request)

        add(collection, "GET", paginate()(list_view), "list", response=list[Read])

        def get_view(request: HttpRequest, pk):
            return get_object_or_404(queryset(), pk=pk)

        get_view.__annotations__ = {"pk": pk_type}
        add(detail, "GET", get_view, "get", response=Read)

    if "POST" in methods:

        def create_view(request: HttpRequest, payload):
            return Status(201, _save(model, model(), payload.model_dump()))

        create_view.__annotations__ = {"payload": schemas.create}
        add(collection, "POST", create_view, "create", response={201: Read})

    if "PUT" in methods:

        def put_view(request: HttpRequest, pk, payload):
            obj = get_object_or_404(queryset(), pk=pk)
            return _save(model, obj, payload.model_dump())

        put_view.__annotations__ = {"pk": pk_type, "payload": schemas.update}
        add(detail, "PUT", put_view, "update", response=Read)

    if "PATCH" in methods:

        def patch_view(request: HttpRequest, pk, payload):
            obj = get_object_or_404(queryset(), pk=pk)
            return _save(model, obj, payload.model_dump(exclude_unset=True))

        patch_view.__annotations__ = {"pk": pk_type, "payload": schemas.patch}
        add(detail, "PATCH", patch_view, "patch", response=Read)

    if "DELETE" in methods:

        def delete_view(request: HttpRequest, pk):
            get_object_or_404(queryset(), pk=pk).delete()
            return Status(204, None)

        delete_view.__annotations__ = {"pk": pk_type}
        add(detail, "DELETE", delete_view, "delete", response={204: None})

    if "HEAD" in methods:

        def head_list_view(request: HttpRequest):
            filtered(request)
            return HttpResponse(status=200)

        add(collection, "HEAD", head_list_view, "head_list")

        def head_detail_view(request: HttpRequest, pk):
            get_object_or_404(queryset(), pk=pk)
            return HttpResponse(status=200)

        head_detail_view.__annotations__ = {"pk": pk_type}
        add(detail, "HEAD", head_detail_view, "head_detail")
