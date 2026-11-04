# django-ninja-expose

Add `@expose()` to a Django model. Get a REST API.

```python
from django.db import models
from django_ninja_expose import expose

@expose()
class Task(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
```

```python
# urls.py
from django.urls import path
from ninja import NinjaAPI
from django_ninja_expose import mount

api = NinjaAPI()
mount(api)  # or api.add_router("", get_router())

urlpatterns = [path("api/", api.urls)]
```

You get `GET/POST /api/Task`, `GET/PUT/PATCH/DELETE/HEAD /api/Task/{pk}`, Django-native
filtering (`?title__icontains=x&completed=false`), Ninja pagination and OpenAPI docs.

## `@expose(path=None, methods=None, fields=None, query=None)`

`None` = automatic, `[]` = none, list = explicit restriction.

| arg | `None` | `[]` | list |
|---|---|---|---|
| `path` | class name | n/a | URL path |
| `methods` | all six (`HEAD` is never implied) | no operations | only these |
| `fields` | all concrete fields + M2M | no fields | only these |
| `query` | all exposed fields | filtering disabled | only these (subset of `fields`) |

Invalid configuration fails at import time (`ExposeConfigurationError` and subclasses);
duplicate paths fail when the router is built.

## Security warning

`@expose()` exposes model data and CRUD operations by default, with no authentication.
Explicitly restrict `methods`, `fields` and `query` for production APIs, and add auth
on your `NinjaAPI`.

## Notes

- Foreign keys and many-to-many fields are represented by primary keys (no nesting).
- Filters accept Django lookups/transforms on whitelisted fields only; relationship traversal is rejected (HTTP 400).
- Writes run Django's `full_clean()`; non-editable fields (e.g. `auto_now_add`) are never writable.
