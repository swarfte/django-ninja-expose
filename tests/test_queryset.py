import json

import pytest
from ninja import NinjaAPI
from ninja.testing import TestClient

from django_ninja_expose import InvalidQuerysetError, expose, mount, registry
from tests.testapp.models import Note

pytestmark = pytest.mark.django_db


def own_notes(request, qs):
    return qs.filter(owner=request.headers.get("X-User"))


@pytest.fixture(autouse=True)
def restore_registry():
    saved = registry.get_registry()
    yield
    registry.clear()
    for model, cfg in saved.items():
        registry.register(model, cfg)


@pytest.fixture
def c():
    registry.clear()
    expose(path="notes", queryset=own_notes)(Note)
    api = NinjaAPI(urls_namespace="qs-test")
    mount(api)
    return TestClient(api)


def as_(user):
    return {"headers": {"X-User": user}}


@pytest.fixture
def notes():
    return Note.objects.create(owner="alice", text="a"), Note.objects.create(owner="bob", text="b")


def test_list_is_scoped(c, notes):
    r = c.get("/notes", **as_("alice"))
    assert [n["owner"] for n in r.json()["items"]] == ["alice"]
    assert c.get("/notes", **as_("nobody")).json()["items"] == []


def test_detail_of_other_user_is_404(c, notes):
    alice, bob = notes
    assert c.get(f"/notes/{alice.pk}", **as_("alice")).status_code == 200
    assert c.get(f"/notes/{bob.pk}", **as_("alice")).status_code == 404


def test_update_and_delete_of_other_user_is_404(c, notes):
    _, bob = notes
    assert c.put(f"/notes/{bob.pk}", json={"owner": "alice", "text": "x"}, **as_("alice")).status_code == 404
    assert c.patch(f"/notes/{bob.pk}", json={"text": "x"}, **as_("alice")).status_code == 404
    assert c.delete(f"/notes/{bob.pk}", **as_("alice")).status_code == 404
    assert Note.objects.filter(pk=bob.pk, text="b").exists()


def test_own_object_can_be_modified_and_deleted(c, notes):
    alice, _ = notes
    assert c.patch(f"/notes/{alice.pk}", json={"text": "new"}, **as_("alice")).status_code == 200
    assert c.delete(f"/notes/{alice.pk}", **as_("alice")).status_code == 204


def test_head_is_scoped(c, notes):
    _, bob = notes
    assert c.request("HEAD", f"/notes/{bob.pk}", **as_("alice")).status_code == 404


def test_filters_cannot_escape_scope(c, notes):
    r = c.get("/notes?owner=bob", **as_("alice"))
    assert r.json()["items"] == []


def test_create_inside_scope_ok(c):
    r = c.post("/notes", json={"owner": "alice", "text": "x"}, **as_("alice"))
    assert r.status_code == 201


def test_create_outside_scope_forbidden_and_rolled_back(c):
    r = c.post("/notes", json={"owner": "bob", "text": "x"}, **as_("alice"))
    assert r.status_code == 403
    assert Note.objects.count() == 0


@pytest.mark.parametrize("bad", ["x", 42, [own_notes]])
def test_invalid_queryset(bad):
    registry.clear()
    with pytest.raises(InvalidQuerysetError):
        expose(queryset=bad)(Note)
