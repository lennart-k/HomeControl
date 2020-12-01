"""auth providers for HomeControl"""
import ipaddress
from typing import Optional, Union

from aiohttp import hdrs, web

from . import AuthManager
from .models import RefreshToken, User


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

        if isinstance(refresh_token, RefreshToken):
            return refresh_token.user

    async def validate_auth_header(
            self,
            request: web.Request) -> Union[RefreshToken, bool, None]:
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
        self.trusted_networks = {}
        for trusted_network in self.cfg.get("trusted-networks", []):
            addresses = trusted_network.get("addresses", [])
            if "address" in trusted_network:
                addresses.append(trusted_network["address"])
            for address in addresses:
                network = ipaddress.ip_network(address)
                self.trusted_networks[network] = {
                    "user": trusted_network["user"]
                }

    async def validate_request(self, request: web.Request) -> Optional[User]:
        remote = request.remote

        # Block forwarded request, they'd be a huge security nightmare
        if request.forwarded:
            return

        for network, data in self.trusted_networks.items():
            if ipaddress.ip_address(remote) in network:
                return self.auth_manager.get_user(data["user"])


AUTH_PROVIDERS = {
    "oauth": OauthAuthProvider,
    "trusted-clients": TrustedClientsAuthProvider
}
