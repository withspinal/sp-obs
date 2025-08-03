import warnings
from functools import wraps


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
