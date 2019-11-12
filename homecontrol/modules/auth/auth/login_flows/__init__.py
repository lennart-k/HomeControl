"""Provides login flows"""

from typing import (
    Union,
    Optional,
    Callable
)
from functools import partial
import uuid
import bcrypt
import voluptuous as vol

from .. import AuthManager
from ..models import User
from ..credential_provider import (
    PasswordCredentialProvider, CredentialProvider
)

# pylint: disable=redefined-builtin,invalid-name


class FlowStep:
    """The class representing the result of a step"""
    user: User
    type: Union["form", "success", "error"]
    error: Optional[str]
    step_id: str
    data: dict
    auth_code: Optional[str]

    def __init__(
            self,
            flow: "LoginFlow",
            step_id: str = None,
            user: User = None,
            type: str = None,
            error: str = None,
            data: dict = None,
            auth_code: str = None,
            form_type: str = None) -> None:
        self.flow = flow
        self.user = user
        self.type = type or ("form" if not error else "error")
        self.error = error
        self.step_id = step_id
        self.data = data
        self.auth_code = auth_code
        self.form_type = form_type

    def to_json(self) -> dict:
        output = {
            "id": self.flow.id,
            "step_id": self.step_id,
            "type": self.type,
            "data": self.data
        }
        if self.error:
            output["error"] = self.error
        if self.auth_code:
            output["auth_code"] = self.auth_code
        if self.form_type:
            output["form_type"] = self.form_type

        return output


class LoginFlow:
    """Abstract class for a login flow"""
    id: str
    current_step: str = "init"
    user: Optional[User]

    def __init__(
            self,
            flow_manager: "FlowManager",
            id: str,
            client_id: str,
            cfg: dict = None) -> None:
        self.client_id = client_id
        self.id = id
        self.flow_manager: FlowManager = flow_manager
        self.auth_manager: AuthManager = self.flow_manager.auth_manager
        self.core = self.auth_manager.core
        self.cfg = cfg or {}

    def get_step(self, step_id: str) -> Optional[Callable]:
        """Returns the coroutine corresponding to a step_id"""
        return getattr(self, f"step_{step_id}", None)

    async def step_init(self, data: dict) -> FlowStep:
        """The first step of the login flow"""

    def destroy(self) -> None:
        """Schedules this flow to be destroyed"""
        self.flow_manager.core.loop.call_soon(
            partial(self.flow_manager.destroy_flow, self.id))

    def set_step(self, step_id: str = None, **kwargs) -> FlowStep:
        """Updates the current step"""
        if step_id:
            self.current_step = step_id
        return FlowStep(
            self,
            step_id=step_id,
            **kwargs
        )

    async def return_auth_code(
            self,
            user: Optional[User] = None,
            client_id: Optional[str] = None) -> FlowStep:
        """Returns the final step with an authorization code"""
        code = await self.auth_manager.create_authorization_code(
            user=user or self.user,
            client_id=client_id or self.client_id
        )
        return FlowStep(self, user=user, type="success", auth_code=code.code)


class FlowManager:
    """The FlowManager manages all the login flows"""

    def __init__(self, auth_manager: AuthManager, cfg: dict):
        self.auth_manager = auth_manager
        self.core = self.auth_manager.core
        self.cfg = cfg
        self.flow_factories = {
            name: self.flow_factory(cfg)
            for name, cfg in self.cfg.items()
        }
        self.flows = {}

    async def create_flow(
            self,
            flow_type: str,
            client_id: str) -> Optional[LoginFlow]:
        """Creates a login flow"""
        factory = self.flow_factories.get(flow_type)
        if factory:
            flow: LoginFlow = await factory(client_id)
            self.flows[flow.id] = flow
            return flow

    def destroy_flow(self, flow_id: str) -> None:
        """Destroys a login flow"""
        self.flows.pop(flow_id, None)

    def flow_factory(self, cfg: dict) -> Callable:
        """
        Returns a factory function for a login flow with certain configuration
        """
        provider = cfg["provider"]

        async def create_flow(client_id: str) -> Optional[LoginFlow]:
            flow_id = uuid.uuid4().hex
            if provider in FLOW_TYPES:
                flow: LoginFlow = FLOW_TYPES[provider](
                    self, flow_id, client_id, cfg=cfg
                )
                return flow

        return create_flow


DUMMY_HASH = b'$2b$12$aZFoxzj4axZgsa1oyGYQmecFwGYFzX/YvObOTCNE6Za9r9ixdUm/y'


class PasswordLoginFlow(LoginFlow):
    """The password login flow"""
    user: User

    def __init__(
            self,
            flow_manager: FlowManager,
            id: str,
            client_id: str,
            cfg: dict = None) -> None:

        super().__init__(flow_manager, id, client_id, cfg=cfg)

        self.mfa_module = self.cfg.get("mfa-module", None)
        self.password_provider: PasswordCredentialProvider = (
            self.auth_manager.credential_providers["password"])
        self.mfa_provider: CredentialProvider = (
            self.auth_manager.credential_providers.get(self.mfa_module))

    async def step_init(self, data: dict) -> FlowStep:
        """The first step"""
        return self.set_step(
            type="form",
            step_id="login",
            data=self.password_provider.form,
            form_type=self.password_provider.namespace
        )

    async def step_login(self, data: dict) -> FlowStep:
        """The actual login step"""
        try:
            data = self.password_provider.schema(data)
        except vol.Invalid as e:
            return FlowStep(self, error=str(e))

        self.user = self.auth_manager.get_user_by_name(data["username"])

        if not self.user:
            bcrypt.checkpw(data["password"].encode(), DUMMY_HASH)
            valid_password = False
        else:
            valid_password = await self.password_provider.validate_login_data(
                self.user, data=data["password"])

        if not valid_password:
            return FlowStep(self, error="Invalid credentials")

        if not self.mfa_module:
            return await self.return_auth_code()
        else:
            return self.set_step(
                type="form",
                step_id="mfa",
                data=self.mfa_provider.form,
                form_type=self.mfa_provider.namespace
            )

    async def step_mfa(self, data: dict) -> FlowStep:
        """The step for multiple-factor authentication"""
        if not self.mfa_module in self.auth_manager.credential_providers:
            return FlowStep(self, error="Invalid MFA module")

        valid_code = await self.mfa_provider.validate_login_data(
            self.user, data=data["code"])

        if valid_code:
            return await self.return_auth_code()

        return FlowStep(self, error="Invalid MFA code")


FLOW_TYPES = {
    "password": PasswordLoginFlow
}
