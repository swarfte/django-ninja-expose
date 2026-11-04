from django.urls import path
from ninja import NinjaAPI

from django_ninja_expose import mount

api = NinjaAPI()
mount(api)

urlpatterns = [path("api/", api.urls)]
