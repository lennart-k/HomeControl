"""Middleware decorator for auth"""
from functools import wraps
from typing import Callable
from aiohttp.web import Request


def needs_auth(
        require_user: bool = True,
        owner_only: bool = False,
        allow_banned: bool = False,
        log_invalid: bool = False) -> Callable:
    """Decorator for a request handler for authentication"""

    # pylint: disable=invalid-name
    def decorator(f: Callable) -> Callable:
        f.use_auth = True
        f.require_user = require_user or owner_only
        f.owner_only = owner_only
        f.allow_banned = allow_banned
        f.log_invalid = log_invalid

        @wraps(f)
        def wrapper(request: Request):
            return f(request)

        return wrapper
    return decorator
