import pytest
from django.db import models

from django_ninja_expose import (
    ExposeConfigurationError,
    InvalidFieldError,
    InvalidQueryFieldError,
    UnsupportedMethodError,
    expose,
    registry,
)
from django_ninja_expose.router import build_router


def make(**kw):
    class Thing(models.Model):
        title = models.CharField(max_length=5)
        secret = models.CharField(max_length=5)

        class Meta:
            app_label = "testapp"

    return expose(**kw)(Thing)


@pytest.fixture(autouse=True)
def restore_registry():
    saved = registry.get_registry()
    yield
    registry.clear()
    for model, cfg in saved.items():
        registry.register(model, cfg)


def test_defaults_resolved():
    model = make()
    cfg = registry.get_registry()[model]
    assert cfg.path == "Thing"
    assert cfg.methods == ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD")
    assert cfg.fields == ("id", "title", "secret") and cfg.query == cfg.fields


def test_query_defaults_to_fields():
    model = make(fields=["id", "title"])
    cfg = registry.get_registry()[model]
    assert cfg.query == ("id", "title")


def test_invalid_method():
    with pytest.raises(UnsupportedMethodError):
        make(methods=["GET", "HELLO"])


def test_invalid_field():
    with pytest.raises(InvalidFieldError, match="hello"):
        make(fields=["id", "hello"])


def test_invalid_query():
    with pytest.raises(InvalidQueryFieldError):
        make(query=["something"])
    with pytest.raises(InvalidQueryFieldError):  # query must be subset of fields
        make(fields=["id", "title"], query=["secret"])


def test_duplicate_path():
    a, b = make(path="dup"), make(path="dup")
    with pytest.raises(ExposeConfigurationError, match="Duplicate expose path: 'dup'"):
        build_router([a, b])
