import warnings
from functools import wraps
from urllib.parse import parse_qsl, urlparse
from opentelemetry.trace import Span
from opentelemetry.util.http import PARAMS_TO_REDACT


def deprecated(replacement=None):
    """Decorator to mark functions as deprecated

    Args:
        replacement: Optional name of the replacement function/method
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            message = f"{func.__name__} is deprecated"
            if replacement:
                message += f", use {replacement} instead"
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def add_request_params_to_span(span: Span, url: str):
    """Add request parameters to span attributes"""
    parsed_url = urlparse(url)
    params = dict(parse_qsl(parsed_url.query))

    for query_parameter, value in params.items():
        if query_parameter not in PARAMS_TO_REDACT:
            span.set_attribute(f"spinal.http.request.query.{query_parameter}", value)
