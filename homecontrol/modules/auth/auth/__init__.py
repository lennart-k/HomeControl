"""Auth module"""
from datetime import datetime, timedelta

from typing import (
    List,
    Dict,
    Optional
)

import logging
import time
import base64
import voluptuous as vol
import jwt

from homecontrol.core import Core
from homecontrol.dependencies.storage import Storage, DictWrapper
from .models import AccessToken, RefreshToken, User, AuthorizationCode

LOGGER = logging.getLogger(__name__)
ACCESS_TOKEN_EXPIRATION = timedelta(minutes=30)


class AuthManager:
    """Object handling authentication"""

    def __init__(self, core: Core) -> None:
        self.core = core
        user_storage = Storage.get_storage(
            self.core, "users", 1,
            storage_init=lambda: {},
            loader=self._load_users,
            dumper=self._dump_users
        )
        self.users = DictWrapper(user_storage)
        user_storage.schedule_save(self.users)

        token_storage = Storage.get_storage(
            self.core, "refresh_tokens", 1,
            storage_init=lambda: {},
            loader=self._load_refresh_tokens,
            dumper=self._dump_refresh_tokens,)
        self.refresh_tokens = DictWrapper(token_storage)
        self.auth_codes: Dict[str, AuthorizationCode] = {}

    # pylint: disable=invalid-name,redefined-builtin
    def get_user(self, id: str) -> Optional[User]:
        """Returns a user by its ID"""
        return self.users.get(id)

    def get_user_by_name(
            self,
            name: str,
            iter_all: bool = True) -> Optional[User]:
        """Returns a user by its name"""
        found_user = None
        for id, user in self.users.items():
            if user.name == name:
                found_user = user
                if not iter_all:
                    return user
        return found_user

    def _load_users(self, data: dict) -> None:
        users = {}
        for id, user_data in data.items():
            users[id] = User(
                name=user_data["name"],
                owner=user_data["owner"],
                id=user_data["id"],
                salted_password=(
                    user_data.get("salted_password")
                    and base64.b64decode(user_data["salted_password"])),
                system_generated=user_data.get("system_generated", False)
            )

        if "system" not in users:
            LOGGER.info("No system user defined. Generating a new one")
            users["system"] = User(
                name="HomeControl System",
                owner=True,
                id="system",
                system_generated=True
            )

        return users

    def _dump_users(self, data: dict) -> dict:
        return {
            user.id: {
                "name": user.name,
                "owner": user.owner,
                "id": user.id,
                "salted_password": (
                    user.salted_password
                    and base64.b64encode(user.salted_password).decode()),
                "system_generated": user.system_generated
            }
            for user in data.values()
        }

    def _load_refresh_tokens(self, data) -> None:
        refresh_tokens = {}
        for id, token_data in data.items():
            refresh_tokens[id] = RefreshToken(
                client_id=token_data["client_id"],
                access_token_expiration=timedelta(
                    seconds=token_data["access_token_expiration"]),
                token=token_data["token"],
                user=self.get_user(token_data.get("user")),
                id=token_data["id"],
                jwt_key=token_data["jwt_key"]
            )
        return refresh_tokens

    def _dump_refresh_tokens(self, data: dict) -> dict:
        return {
            refresh_token.id: {
                "client_id": refresh_token.client_id,
                "access_token_expiration":
                    refresh_token.access_token_expiration.total_seconds(),
                "token": refresh_token.token,
                "id": refresh_token.id,
                "user": refresh_token.user and refresh_token.user.id,
                "jwt_key": refresh_token.jwt_key
            }
            for refresh_token in data.values()
        }

    async def create_refresh_token(
            self,
            client_id: str,
            user: Optional[User] = None,
            access_token_expiration: Optional[timedelta] = None,
    ) -> RefreshToken:
        """Creates a refresh token"""
        refresh_token = RefreshToken(
            client_id=client_id,
            user=user,
            access_token_expiration=(
                access_token_expiration or ACCESS_TOKEN_EXPIRATION)
        )
        self.refresh_tokens[refresh_token.id] = refresh_token
        return refresh_token

    def get_refresh_token_by_string(self,
                                    token: str) -> Optional[RefreshToken]:
        """Returns a refresh token by its token string"""
        for refresh_token in self.refresh_tokens.values():
            if refresh_token.token == token:
                return refresh_token

    def revoke_refresh_token(self, token_id: str) -> None:
        """Revokes an access token"""
        if token_id in self.refresh_tokens:
            del self.refresh_tokens[id]

    async def create_authorization_code(
            self,
            client_id: str,
            expiration: timedelta = None,
            state: str = None,
            access_token_expiration: timedelta = None,
            user: Optional[User] = None) -> AuthorizationCode:
        """Creates an authorization code"""
        code = AuthorizationCode(
            client_id=client_id,
            expiration=expiration or timedelta(seconds=60),
            state=state,
            access_token_expiration=access_token_expiration,
            user=user
        )
        self.auth_codes[code.code] = code
        return code

    def remove_authorization_code(self, code: AuthorizationCode) -> None:
        """Removes an authorization code"""
        self.auth_codes.pop(code.code)

    async def create_user(self,
                          name: str,
                          owner: bool = False,
                          salted_password: str = None,
                          system_generated: bool = False
                          ) -> User:
        """Creates a user"""
        user = User(
            name=name,
            owner=owner,
            salted_password=salted_password,
            system_generated=system_generated
        )
        self.users[user.id] = user
        return user

    async def create_access_token(
            self,
            refresh_token: RefreshToken
    ) -> AccessToken:
        """
        Creates access token from refresh token
        """
        now = datetime.now()
        token = jwt.encode(
            {
                "iss": refresh_token.id,
                "iat": now,
                "exp": now + refresh_token.access_token_expiration
            },
            refresh_token.jwt_key,
            algorithm="HS256").decode()
        return AccessToken(
            token=token,
            expiration=now + refresh_token.access_token_expiration
        )

    async def validate_access_token(
            self,
            token: str
    ) -> Optional[RefreshToken]:
        """
        Returns the corresponding refresh token
        if the access token is valid
        """
        try:
            decoded_token = jwt.decode(token, verify=False)
        except jwt.InvalidTokenError:
            return

        refresh_token = self.refresh_tokens.get(decoded_token.get("iss"), None)
        if not refresh_token:
            return

        # Check if token is expired
        if time.time() > decoded_token.get("exp"):
            return

        try:
            jwt.decode(
                token,
                refresh_token.jwt_key,
                issuer=refresh_token.id,
                algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return

        return refresh_token
