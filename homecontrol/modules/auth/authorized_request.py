"""An authorized request"""
from aiohttp.web import Request
from .auth.models import User


class AuthorizedRequest(Request):
    """An authorized request"""
    user = User
