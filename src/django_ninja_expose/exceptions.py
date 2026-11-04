"""Exceptions raised by django-ninja-expose."""


class ExposeConfigurationError(Exception):
    """Raised at startup when an ``@expose()`` configuration is invalid."""


class UnsupportedMethodError(ExposeConfigurationError):
    """An unsupported HTTP method was requested."""


class InvalidFieldError(ExposeConfigurationError):
    """``fields`` references a field the model does not have."""


class InvalidQueryFieldError(ExposeConfigurationError):
    """``query`` references an unknown field or a field that is not exposed."""


class InvalidAuthError(ExposeConfigurationError):
    """``auth`` is neither ``INHERIT``, ``None`` nor a callable / list of callables."""


class InvalidLookupError(Exception):
    """A request used an invalid filter field or lookup (mapped to HTTP 400)."""
