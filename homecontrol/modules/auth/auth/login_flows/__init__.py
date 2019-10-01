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
            step_id: str = None,
            user: User = None,
            type: str = None,
            error: str = None,
            data: dict = None,
            auth_code: str = None) -> None:
        self.user = user
        self.type = type or ("form" if not error else "error")
        self.error = error
        self.step_id = step_id
        self.data = data
        self.auth_code = auth_code


class LoginFlow:
    """Abstract class for a login flow"""
    id: str
    current_step: str = "init"

    def __init__(
            self,
            auth_manager: AuthManager,
            flow_manager: "FlowManager",
            id: str,
            client_id: str) -> None:
        self.client_id = client_id
        self.id = id
        self.auth_manager: AuthManager = auth_manager
        self.flow_manager: FlowManager = flow_manager
        self.core = self.auth_manager.core

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
            step_id=step_id,
            **kwargs
        )


class FlowManager:
    """The FlowManager manages all the login flows"""

    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.core = self.auth_manager.core
        self.flows = {}

    async def create_flow(
            self,
            flow_type: str,
            client_id: str) -> Optional[LoginFlow]:
        """Creates a login flow"""
        flow_id = uuid.uuid4().hex
        if flow_type in FLOW_TYPES:
            flow: LoginFlow = FLOW_TYPES[flow_type](
                self.auth_manager, self, flow_id, client_id)
            self.flows[flow_id] = flow
            return flow

    def destroy_flow(self, flow_id: str) -> None:
        """Destroys a login flow"""
        self.flows.pop(flow_id, None)


DUMMY_HASH = b'$2b$12$aZFoxzj4axZgsa1oyGYQmecFwGYFzX/YvObOTCNE6Za9r9ixdUm/y'


class PasswordLoginFlow(LoginFlow):
    """The password login flow"""
    user: User

    async def step_init(self, data: dict) -> FlowStep:
        """The first step"""
        return self.set_step(
            type="form",
            step_id="login",
            data={
                "username": "String",
                "password": "Password"
            }
        )

    async def step_login(self, data: dict) -> FlowStep:
        """The actual login step"""
        try:
            data = vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str
            })(data)
        except vol.Invalid as e:
            return FlowStep(error=str(e))

        self.user = self.auth_manager.get_user_by_name(data["username"])

        if not self.user:
            bcrypt.checkpw(data["password"].encode(), DUMMY_HASH)
            valid_password = False
        else:
            valid_password = self.user.match_password(data["password"])

        if not valid_password:
            return FlowStep(error="Invalid credentials")

        code = await self.auth_manager.create_authorization_code(
            client_id=self.client_id,
            user=self.user
        )

        return FlowStep(user=self.user, type="success", auth_code=code.code)


FLOW_TYPES = {
    "password": PasswordLoginFlow
}
