SECRET_KEY = "test"
DEBUG = True
USE_TZ = True
ROOT_URLCONF = "tests.urls"
INSTALLED_APPS = ["django.contrib.contenttypes", "tests.testapp"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
