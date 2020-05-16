"""The auth endpoints"""
from typing import TYPE_CHECKING
from datetime import timedelta
from json import JSONDecodeError
from aiohttp import web, hdrs
import voluptuous as vol
from homecontrol.modules.api.view import APIView
from homecontrol.dependencies.json_response import JSONResponse
from .decorator import needs_auth
if TYPE_CHECKING:
    from .auth import AuthManager
    from .auth.login_flows import FlowManager
    from .module import Module
    from .auth.credential_provider import CredentialProvider


GRANT_TYPES = ("password", "code", "refresh_token")
AUTHORIZE_PAYLOAD_SCHEMA = vol.Schema({
    vol.Required("client_id"): str,
    vol.Optional("redirect_uri", default=None): vol.Any(str, None),
    vol.Optional("response_type", default="code"): vol.Any(
        "code", "token"
    ),
    vol.Optional("state", default=None): vol.Any(str, None),
})
TOKEN_PAYLOAD_SCHEMA = vol.Schema({
    vol.Required("grant_type"): vol.Any(*GRANT_TYPES),
    vol.Required("client_id"): str,
}, extra=vol.ALLOW_EXTRA)
PASSWORD_SCHEMA = TOKEN_PAYLOAD_SCHEMA.extend({
    vol.Required("username"): str,
    vol.Required("password"): str
}, extra=vol.PREVENT_EXTRA)
AUTH_CODE_SCHEMA = TOKEN_PAYLOAD_SCHEMA.extend({
    vol.Required("code"): str
}, extra=vol.PREVENT_EXTRA)
REFRESH_TOKEN_SCHEMA = TOKEN_PAYLOAD_SCHEMA.extend({
    vol.Required("refresh_token"): str
}, extra=vol.PREVENT_EXTRA)


def add_routes(app: web.Application):
    """Add the auth routes"""
    LongLivedTokenView.register_view(app)
    LoginFlowProvidersView.register_view(app)
    FlowStepView.register_view(app)
    CreateLoginFlowView.register_view(app)
    BindCredentialsView.register_view(app)
    CreateUserView.register_view(app)
    TokenView.register_view(app)
    UserInfoView.register_view(app)


class AuthView(APIView):
    """An APIView with access to the auth module"""
    auth: "Module"
    flow_manager: "FlowManager"
    auth_manager: "AuthManager"

    def __init__(self, request):
        super().__init__(request)
        self.auth = request.app["auth"]
        self.flow_manager = self.auth.flow_manager
        self.auth_manager = self.auth.auth_manager


@needs_auth(owner_only=True, log_invalid=True)
class LongLivedTokenView(AuthView):
    """
    Generates a long-lived access token
    This token will be valid for 10 years
    """
    path = "/long_lived_token"

    async def post(self) -> JSONResponse:
        """POST /long_lived_token"""
        try:
            data = vol.Schema({
                vol.Required("client_id"): str,
                vol.Optional(
                    "client_name", default=None): vol.Any(str, None)
            })(await self.request.json())
        except (vol.Invalid, JSONDecodeError) as e:
            return self.error(e)

        refresh_token = await self.auth_manager.create_refresh_token(
            client_id=data["client_id"],
            user=self.request["user"],
            access_token_expiration=timedelta(days=3650),
            client_name=data["client_name"]
        )
        access_token = await self.auth_manager.create_access_token(
            refresh_token)

        return JSONResponse({
            "access_token": access_token.token,
            "token_type": "bearer",
            "expires_in": access_token.expiration,
            "refresh_token": refresh_token.token,
        }, headers={
            "Cache-Control": "no-store"
        })


class LoginFlowProvidersView(AuthView):
    """Returns a list of login providers"""
    path = "/login_flow_providers"

    async def get(self) -> JSONResponse:
        """GET /login_flow_providers"""
        return self.json(list(self.flow_manager.flow_factories.keys()))


class CreateLoginFlowView(AuthView):
    """Creates a login flow"""
    path = "/login_flow"

    async def post(self) -> JSONResponse:
        """POST /login_flow"""
        try:
            data = vol.Schema({
                vol.Required("provider"): vol.Any(
                    *self.flow_manager.flow_factories.keys()),
                vol.Required("client_id"): str
            })(await self.request.json())
        except (vol.Invalid, JSONDecodeError) as e:
            return self.error(e)

        flow = await self.flow_manager.create_flow(
            data["provider"],
            data["client_id"])
        if not flow:
            return self.error("Login flow does not exist")

        first_result = await flow.step_init(data)

        return self.json(first_result.to_json())


class FlowStepView(AuthView):
    """Executes the current login_flow step"""
    path = "/login_flow/{flow_id}"

    async def post(self) -> JSONResponse:
        """POST /login_flow/{flow_id}"""
        try:
            data = await self.request.json()
        except JSONDecodeError as e:
            return self.error(e)

        flow = self.flow_manager.flows.get(self.request.match_info["flow_id"])

        if not flow:
            return self.error("Login flow does not exist")

        step = flow.get_step(flow.current_step)
        step_result = await step(data)

        return self.json(step_result.to_json())


@needs_auth(require_user=True)
class BindCredentialsView(AuthView):
    """Binds credentials to a user"""
    path = "/bind_credentials"

    async def post(self) -> JSONResponse:
        """POST /bind_credentials"""
        try:
            data = vol.Schema({
                vol.Required("provider", default="password"): vol.Any(
                    *self.auth_manager.credential_providers.keys()),
                vol.Optional("user", default=None): vol.Any(str, None),
                vol.Optional("data", default=None): object
            })(await self.request.json())
        except (vol.Invalid, JSONDecodeError) as e:
            return JSONResponse(error=str(e))

        if data["user"] and not self.request["user"].owner:
            return JSONResponse(error="Unauthorized", status_code=401)

        user = self.auth_manager.get_user(data["user"]) or self.request["user"]

        provider: "CredentialProvider" = (
            self.auth_manager.credential_providers[data["provider"]])

        creds, return_data = await provider.create_credentials(
            user, data["data"])
        self.auth_manager.users.schedule_save()

        return JSONResponse({
            "credential_id": creds.credential_id,
            "data": return_data
        })


@needs_auth(owner_only=True, log_invalid=True)
class CreateUserView(AuthView):
    """Creates a user"""
    path = "/create_user"

    async def post(self) -> JSONResponse:
        """POST /create_user"""
        payload_schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("password"): str,
            vol.Optional("is_owner", default=False): bool,
        })
        payload = payload_schema(await self.request.json())

        user = await self.auth_manager.create_user(
            name=payload["name"],
            owner=payload["is_owner"]
        )

        provider: "CredentialProvider" = (
            self.auth_manager.credential_providers["password"])

        await provider.create_credentials(user, payload["password"])

        self.auth_manager.users.schedule_save()

        return self.json({
            "user_id": user.id
        })


class TokenView(AuthView):
    """The OAuth2 /token endpoint"""
    path = "/token"

    async def post(self) -> JSONResponse:
        """POST /token"""
        try:
            data = dict((await self.request.post()).items())
            payload = TOKEN_PAYLOAD_SCHEMA(data)
        except vol.Invalid as e:
            path = ', '.join(str(var) for var in e.path)
            return self.json({
                "error": "invalid_request",
                "error_description": f"Invalid parameters: {path}"
            }, status_code=400)

        if payload["grant_type"] == "code":
            try:
                payload = AUTH_CODE_SCHEMA(payload)
            except vol.Invalid:
                return self.json({
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code"
                }, status_code=400)

            code = self.auth_manager.auth_codes.get(payload["code"])
            if not code:
                return self.json({
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code"
                }, status_code=400)

            if code.expired:
                return self.json({
                    "error": "invalid_grant",
                    "error_description": "Authorization code expired"
                }, status_code=400)

            self.auth_manager.remove_authorization_code(code)

            refresh_token = await self.auth_manager.create_refresh_token(
                client_id=code.client_id,
                access_token_expiration=code.access_token_expiration,
                user=code.user
            )

        if payload["grant_type"] == "password":
            try:
                payload = PASSWORD_SCHEMA(payload)
            except vol.Invalid:
                return self.json({
                    "error": "invalid_grant",
                    "error_description": "Invalid credentials"
                }, status_code=400)

            cred_provider: "CredentialProvider" = (
                self.auth_manager.credential_providers["password"])

            user = self.auth_manager.get_user_by_name(payload["username"])

            login_valid = await cred_provider.validate_login_data(
                user,
                payload["password"]
            )

            if not login_valid:
                return self.json({
                    "error": "invalid_grant",
                    "error_description": "Invalid credentials"
                }, status_code=400)

            refresh_token = await self.auth_manager.create_refresh_token(
                payload["client_id"],
                user=user)

        if payload["grant_type"] == "refresh_token":
            try:
                payload = REFRESH_TOKEN_SCHEMA(payload)
            except vol.Invalid as e:
                if "refresh_token" in e.path:
                    return self.json({
                        "error": "invalid_grant",
                        "error_description": "Grant type 'refresh_token'"
                                             "needs a 'refresh_token'"
                                             "parameter"
                    }, status_code=400)

                invalid = ', '.join(e.path)
                return self.json({
                    "error": "invalid_request",
                    "error_description": f"Invalid parameters: {invalid}"
                }, status_code=400)

            refresh_token = self.auth_manager.get_refresh_token_by_string(
                payload["refresh_token"]
            )

            if not refresh_token:
                return self.json({
                    "error": "invalid_grant",
                    "error_description": "Invalid refresh token"
                }, status_code=400)

        access_token = await self.auth_manager.create_access_token(
            refresh_token)

        return JSONResponse({
            "access_token": access_token.token,
            "token_type": "bearer",
            "expires_in": access_token.expiration,
            "refresh_token": refresh_token.token,
        }, headers={
            hdrs.CACHE_CONTROL: "no-store"
        })

@needs_auth()
class UserInfoView(APIView):
    """Returns information about the current user"""
    path = "/user_info"

    async def get(self) -> JSONResponse:
        """GET /user_info"""
        user = self.request["user"]

        return self.json({
            "name": user.name,
            "owner": user.owner,
            "system_generated": user.system_generated,
            "id": user.id
        })
