import pytest
from ninja import NinjaAPI
from ninja.security import APIKeyHeader
from ninja.testing import TestClient

from django_ninja_expose import INHERIT, InvalidAuthError, expose, mount, registry
from django_ninja_expose.router import build_router
from tests.testapp.models import Tag

pytestmark = pytest.mark.django_db


class Key(APIKeyHeader):
    param_name = "X-Key"

    def authenticate(self, request, key):
        return key if key == "secret" else None


@pytest.fixture(autouse=True)
def restore_registry():
    saved = registry.get_registry()
    yield
    registry.clear()
    for model, cfg in saved.items():
        registry.register(model, cfg)


def client_for(auth, api_auth=None):
    registry.clear()
    expose(path="tags", auth=auth)(Tag)
    api = NinjaAPI(auth=api_auth, urls_namespace=f"auth-{id(auth)}-{id(api_auth)}")
    mount(api)
    return TestClient(api)


def test_default_is_inherit():
    registry.clear()
    expose()(Tag)
    assert registry.get_registry()[Tag].auth is INHERIT


def test_inherit_uses_api_auth():
    c = client_for(INHERIT, api_auth=Key())
    assert c.get("/tags").status_code == 401
    assert c.get("/tags", headers={"X-Key": "secret"}).status_code == 200


def test_inherit_without_api_auth_is_open():
    assert client_for(INHERIT).get("/tags").status_code == 200


def test_none_disables_api_auth():
    assert client_for(None, api_auth=Key()).get("/tags").status_code == 200


def test_custom_auth_overrides_api_auth():
    c = client_for(Key(), api_auth=lambda request: "api-user")
    assert c.get("/tags").status_code == 401
    assert c.get("/tags", headers={"X-Key": "secret"}).status_code == 200


def test_callable_auth():
    c = client_for(lambda request: request.headers.get("X-Key") == "secret" or None)
    assert c.get("/tags").status_code == 401
    assert c.get("/tags", headers={"X-Key": "secret"}).status_code == 200


def test_list_of_auth():
    c = client_for([Key(), lambda request: None])
    assert c.get("/tags").status_code == 401
    assert c.get("/tags", headers={"X-Key": "secret"}).status_code == 200


@pytest.mark.parametrize("bad", ["django_auth", 42, [], [Key(), "x"]])
def test_invalid_auth(bad):
    registry.clear()
    with pytest.raises(InvalidAuthError):
        expose(auth=bad)(Tag)


def test_build_router_still_works():
    registry.clear()
    expose(auth=None)(Tag)
    assert build_router() is not None
