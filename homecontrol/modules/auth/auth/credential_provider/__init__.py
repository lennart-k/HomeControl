"""Credential providers"""

import base64
import hashlib
from typing import Optional
import bcrypt
import pyotp

from ..models import User, Credentials

DUMMY_HASH = b'$2b$12$aZFoxzj4axZgsa1oyGYQmecFwGYFzX/YvObOTCNE6Za9r9ixdUm/y'


class CredentialProvider:
    """Abstract class for credential providers"""

    namespace = "example"

    def __init__(self, auth_manager) -> None:
        self.auth_manager = auth_manager
        self.core = auth_manager.core

    async def create_credentials(
            self, user: User, data: object) -> (Credentials, Optional[object]):
        """
        Creates credentials for a user

        Returns:
            Credentials The credential object
            Optional[object] Data to return to the API caller
                             For example a QR code when setting up TOTP
        """
        raise NotImplementedError()

    async def validate_login_data(self, user: User, data: object) -> bool:
        """Validates the input credentials against the user"""
        return False

    def get_credentials(
            self, user: User, credential_id: str) -> Optional[Credentials]:
        """Returns the credentials for a user"""
        return user.credentials.get(self.namespace, {}).get(credential_id)

    def get_primary_credentials(self, user: User) -> Optional[Credentials]:
        """Returns the first Credentials object from the user's credentials"""
        return next(
            iter(user.credentials.get(self.namespace, {}).values()), None)

    async def remove_credentials(self, user: User, credential_id: str) -> None:
        """Removes credentials from a user"""
        if credential_id in user.credentials.get(self.namespace):
            del user.credentials[self.namespace][credential_id]


class PasswordCredentialProvider(CredentialProvider):
    """Provides password credentials"""

    namespace = "password"

    # pylint: disable=arguments-differ
    async def create_credentials(
            self, user: User, data: str) -> (Credentials, Optional[object]):
        """Creates credentials for a user"""
        user.credentials.setdefault(self.namespace, {})

        hashed = base64.b64encode(
            hashlib.sha256(data.encode()).digest())
        salted = base64.b64encode(
            bcrypt.hashpw(hashed, bcrypt.gensalt(12))).decode()

        creds = Credentials(
            user=user,
            provider=self.namespace,
            data=salted,
        )
        user.credentials[self.namespace] = {creds.credential_id: creds}

        return creds, None

    async def validate_login_data(self, user: User, data: dict) -> bool:
        """Validates the password against the user input"""
        hashed = base64.b64encode(
            hashlib.sha256(data.encode()).digest())

        creds = self.get_primary_credentials(user)

        if creds:
            return bcrypt.checkpw(hashed, base64.b64decode(creds.data))
        else:
            bcrypt.checkpw(hashed, DUMMY_HASH)
            return False


class TOTPCredentialProvider(CredentialProvider):
    """Provides TOTP based authentication"""
    namespace = "totp"

    async def create_credentials(
            self, user: User, data: dict) -> (Credentials, Optional[object]):
        user.credentials.setdefault(self.namespace, {})

        secret = pyotp.random_base32()
        creds = Credentials(
            user=user,
            provider=self.namespace,
            data=secret
        )
        user.credentials[self.namespace] = {creds.credential_id: creds}
        return creds, {
            "secret": secret,
            "url": pyotp.TOTP(secret).provisioning_uri(user.name)
        }

    async def validate_login_data(self, user: User, data: str) -> bool:
        for creds in user.credentials.get(self.namespace, {}).values():
            if pyotp.TOTP(creds.data).verify(data):
                return True
        return False


CREDENTIAL_PROVIDERS = {
    "password": PasswordCredentialProvider,
    "totp": TOTPCredentialProvider
}
