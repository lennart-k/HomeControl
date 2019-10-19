"""auth providers for HomeControl"""
from socket import gethostbyname
from typing import Optional
from aiohttp import web, hdrs
from . import AuthManager
from .models import User, RefreshToken


class AuthProvider:
    """
    Abstract class for an authentication provider
    An authentication provider is an object that takes an HTTP request
    and optionally returns a User
    """
    def __init__(self, auth_manager: AuthManager, cfg) -> None:
        self.auth_manager = auth_manager
        self.cfg = cfg

    async def validate_request(
            self,
            request: web.Request) -> Optional[User]:
        """Checks if a request is authenticated and returns a user"""
        return None


class OauthAuthProvider(AuthProvider):
    """
    Allows request authentication with an access token
    """
    async def validate_request(self, request: web.Request) -> Optional[User]:
        refresh_token = await self.validate_auth_header(request)

        if refresh_token:
            return refresh_token.user

    async def validate_auth_header(
            self,
            request: web.Request) -> Optional[RefreshToken]:
        """Validates the auth header"""
        auth_header = request.headers.get(hdrs.AUTHORIZATION)
        if not auth_header:
            return False
        if " " not in auth_header:
            return False

        auth_type, token_value = auth_header.split(" ", 1)

        if auth_type == "Bearer":
            return await self.auth_manager.validate_access_token(token_value)


class TrustedClientsAuthProvider(AuthProvider):
    """Allows clients to identify by their network address"""
    def __init__(self, auth_manager: AuthManager, cfg: dict) -> None:
        super().__init__(auth_manager, cfg)
        self.trusted_clients = {}
        for trusted_client in self.cfg["trusted-addresses"]:
            self.trusted_clients[gethostbyname(trusted_client["address"])] = {
                "user": trusted_client["user"]
            }

    async def validate_request(self, request: web.Request) -> Optional[User]:
        remote = request.remote

        if request.forwarded:
            remote = request.forwarded[0].get("for")

        if remote in self.trusted_clients:
            return self.auth_manager.get_user(
                self.trusted_clients[remote]["user"]
            )

AUTH_PROVIDERS = {
    "oauth": OauthAuthProvider,
    "trusted-clients": TrustedClientsAuthProvider
}
