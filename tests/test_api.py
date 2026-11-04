import json
import uuid

import pytest
from django.test import Client

from tests.testapp.models import Memo, Project, Tag, Task

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


def send(client, method, url, data=None):
    return getattr(client, method)(url, json.dumps(data or {}), content_type="application/json")


def test_crud_roundtrip(client):
    p = Project.objects.create(name="P")
    t = Tag.objects.create(label="a")
    r = send(client, "post", "/api/tasks", {"title": "x", "project": p.pk, "tags": [t.pk]})
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["project"] == p.pk and body["tags"] == [t.pk]
    assert body["created_at"]
    tid = body["id"]

    assert client.get(f"/api/tasks/{tid}").json()["title"] == "x"
    r = send(client, "put", f"/api/tasks/{tid}", {"title": "y", "priority": 3})
    assert r.status_code == 200 and r.json()["priority"] == 3
    r = send(client, "patch", f"/api/tasks/{tid}", {"completed": True})
    assert r.json()["completed"] is True and r.json()["title"] == "y"
    assert client.head(f"/api/tasks/{tid}").status_code == 200
    assert client.head("/api/tasks").status_code == 200
    assert client.delete(f"/api/tasks/{tid}").status_code == 204
    assert client.get(f"/api/tasks/{tid}").status_code == 404


def test_created_at_not_writable(client):
    r = send(client, "post", "/api/tasks", {"title": "x", "created_at": "2000-01-01T00:00:00Z"})
    assert r.status_code == 201
    assert not r.json()["created_at"].startswith("2000")


def test_invalid_payload(client):
    assert send(client, "post", "/api/tasks", {"priority": 1}).status_code == 422
    assert send(client, "post", "/api/tasks", {"title": "x", "project": 999}).status_code == 422
    assert send(client, "post", "/api/tasks", {"title": "x", "tags": [999]}).status_code == 422


def test_pagination_and_filters(client):
    for i in range(5):
        Task.objects.create(title=f"t{i}", priority=i, completed=i % 2 == 0)
    assert client.get("/api/tasks?limit=2").json()["count"] == 5
    assert len(client.get("/api/tasks?limit=2").json()["items"]) == 2
    assert client.get("/api/tasks?priority=3").json()["count"] == 1
    assert client.get("/api/tasks?priority__gte=3").json()["count"] == 2
    assert client.get("/api/tasks?priority__lte=1").json()["count"] == 2
    assert client.get("/api/tasks?completed=false").json()["count"] == 2
    assert client.get("/api/tasks?priority__gte=1&completed=true").json()["count"] == 2
    year = Task.objects.first().created_at.year
    assert client.get(f"/api/tasks?created_at__year={year}").json()["count"] == 5
    assert client.get(f"/api/tasks?created_at__year__gte={year}").json()["count"] == 5


@pytest.mark.parametrize(
    "qs",
    [
        "title=t1",  # not in query whitelist
        "priority__bogus=1",
        "bogus=1",
        "project__name=x",
        "priority__gte=abc",
    ],
)
def test_invalid_filters(client, qs):
    assert client.get(f"/api/tasks?{qs}").status_code == 400


def test_default_query_all_fields(client):
    Project.objects.create(name="Django")
    assert client.get("/api/Project?name__icontains=djan").json()["count"] == 1
    assert client.get("/api/Project?name__icontains=zzz").json()["count"] == 0


def test_uuid_pk(client):
    r = send(client, "post", "/api/Document", {"title": "d"})
    assert r.status_code == 201
    pk = r.json()["id"]
    uuid.UUID(pk)
    assert client.get(f"/api/Document/{pk}").status_code == 200
    assert client.get("/api/Document/not-a-uuid").status_code == 422


def test_memo_restrictions(client):
    r = send(client, "post", "/api/Memo", {"title": "m", "secret": "s"})
    assert r.json() == {"id": 1, "title": "m"}
    assert Memo.objects.get().secret == "x"
    assert client.get("/api/Memo?title=m").status_code == 400  # query=[]
    assert client.put("/api/Memo/1").status_code == 405
    assert client.delete("/api/Memo/1").status_code == 405
    assert client.head("/api/Memo").status_code == 405  # HEAD not implied by GET


def test_openapi(client):
    schema = client.get("/api/openapi.json").json()
    assert "/api/tasks/{pk}" in schema["paths"]
    assert "/api/Memo" in schema["paths"]
