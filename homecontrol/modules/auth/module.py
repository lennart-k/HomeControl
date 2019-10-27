"""Provides OAuth2 for HomeControl"""
from typing import Callable
import logging
from json import JSONDecodeError
from datetime import timedelta
from aiohttp import web, hdrs
import voluptuous as vol
from homecontrol.dependencies.json_response import JSONResponse
from homecontrol.dependencies.resolve_path import resolve_path
from homecontrol.core import Core

from .auth import AuthManager
from .auth.login_flows import FlowManager
from .auth.credential_provider import CredentialProvider
from .auth.auth_providers import AUTH_PROVIDERS
from .decorator import needs_auth

LOGGER = logging.getLogger(__name__)

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

CONFIG_SCHEMA = vol.Schema({
    vol.Required("providers"): vol.Schema([
        vol.Schema({
            vol.Required("type"): str
        }, extra=vol.ALLOW_EXTRA)
    ]),
    vol.Required("login-flows", default={}): object
})


class Module:
    """The authentication module"""
    core: Core

    async def init(self) -> None:
        """Initialises the module"""
        self.cfg = await self.core.cfg.register_domain(
            "auth", schema=CONFIG_SCHEMA)
        self.core.event_engine.register(
            "http_add_main_middlewares")(self.add_middlewares)
        self.core.event_engine.register(
            "http_add_api_middlewares")(self.add_middlewares)
        self.core.event_engine.register(
            "http_add_api_routes")(self.add_api_routes)

        self.static_folder = resolve_path(
            "@/www", config_dir=self.core.cfg_dir)

        self.auth_manager = AuthManager(self.core)
        self.flow_manager = FlowManager(
            self.auth_manager, self.cfg["login-flows"])

        self.auth_providers = {
            cfg["type"]: AUTH_PROVIDERS[cfg["type"]](self.auth_manager, cfg)
            for cfg in self.cfg["providers"]
        }

    def _log_invalid_auth(self, request: web.Request) -> None:
        LOGGER.warning("Unauthorized API request: %s %s from %s "
                       "with %s",
                       request.method,
                       request.path,
                       request.host,
                       request.headers.get("User-Agent"))

    async def add_middlewares(self, event, middlewares: list) -> None:
        """Adds the auth middleware to the API app"""
        @middlewares.append
        @web.middleware
        async def check_authentication(request: web.Request,
                                       handler: Callable) -> web.Response:

            if getattr(handler, "allow_banned", False):
                return await handler(request)

            # pylint: disable=singleton-comparison
            for provider_name, provider in self.auth_providers.items():
                request.user = user = await provider.validate_request(request)
                if user is not None:
                    break

            # user is False means access is forbidden
            if user is False:
                if handler.log_invalid:
                    self._log_invalid_auth(request)
                raise web.HTTPUnauthorized(
                    text="401: You are banned from using this endpoint")

            # Owner required but user is not owner
            if (getattr(handler, "owner_only", False)
                    and not getattr(user, "owner", False)):
                if handler.log_invalid:
                    self._log_invalid_auth(request)
                raise web.HTTPUnauthorized(
                    text="401: You need owner permissions for this endpoint")

            # No user found
            if getattr(handler, "require_user", False) and not user:
                if handler.log_invalid:
                    self._log_invalid_auth(request)
                raise web.HTTPUnauthorized(
                    text="401: You need to log in for this endpoint")

            return await handler(request)

        return middlewares

    async def add_api_routes(self, event, router: web.RouteTableDef) -> None:
        """Adds the API routes"""
        @router.post("/auth/long_lived_token")
        @needs_auth(owner_only=True, log_invalid=True)
        async def get_long_lived_token(
                request: web.Request) -> JSONResponse:
            """
            Generates a long-lived access token
            This token will be valid for 10 years
            """
            try:
                data = vol.Schema({
                    vol.Required("client_id"): str,
                    vol.Optional(
                        "client_name", default=None): vol.Any(str, None)
                })(await request.json())
            except (vol.Invalid, JSONDecodeError) as e:
                return JSONResponse(error=str(e))

            refresh_token = await self.auth_manager.create_refresh_token(
                client_id=data["client_id"],
                user=request.user,
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

        @router.get("/auth/login_flow_providers")
        async def get_login_flow_providers(
                request: web.Request) -> JSONResponse:
            """Returns a list of login providers"""
            return JSONResponse(list(self.flow_manager.flow_factories.keys()))

        @router.post("/auth/login_flow")
        async def create_login_flow(request: web.Request) -> JSONResponse:
            """Creates a login flow"""
            try:
                data = vol.Schema({
                    vol.Required("provider"): vol.Any(
                        *self.flow_manager.flow_factories.keys()),
                    vol.Required("client_id"): str
                })(await request.json())
            except (vol.Invalid, JSONDecodeError) as e:
                return JSONResponse(error=str(e))

            flow = await self.flow_manager.create_flow(
                data["provider"],
                data["client_id"])
            if not flow:
                return JSONResponse(error="Login flow does not exist")

            first_result = await flow.step_init(data)

            output = {
                "id": flow.id,
                "step_id": first_result.step_id,
                "type": first_result.type,
                "data": first_result.data
            }
            # TODO REWRITE!
            if first_result.error:
                output["error"] = first_result.error
            if first_result.auth_code:
                output["auth_code"] = first_result.auth_code
            if first_result.form_type:
                output["form_type"] = first_result.form_type

            return JSONResponse(output)

        @router.post("/auth/login_flow/{flow_id}")
        async def do_login_flow_step(request: web.Request) -> JSONResponse:
            """Executes the current login_flow step"""
            try:
                data = await request.json()
            except JSONDecodeError as e:
                return JSONResponse(error=str(e))

            flow = self.flow_manager.flows.get(request.match_info["flow_id"])

            if not flow:
                return JSONResponse(error="Login flow does not exist")

            step = flow.get_step(flow.current_step)
            step_result = await step(data)

            output = {
                "id": flow.id,
                "step_id": step_result.step_id,
                "type": step_result.type,
                "data": step_result.data
            }
            # TODO REWRITE!
            if step_result.error:
                output["error"] = step_result.error
            if step_result.auth_code:
                output["auth_code"] = step_result.auth_code
            if step_result.form_type:
                output["form_type"] = step_result.form_type
            return JSONResponse(output)

        @router.post("/auth/bind_credentials")
        @needs_auth(require_user=True)
        async def bind_credentials(request: web.Request) -> JSONResponse:
            """Binds credentials to a user"""
            try:
                data = vol.Schema({
                    vol.Required("provider", default="password"): vol.Any(
                        *self.auth_manager.credential_providers.keys()),
                    vol.Optional("user", default=None): vol.Any(str, None),
                    vol.Optional("data", default=None): object
                })(await request.json())
            except (vol.Invalid, JSONDecodeError) as e:
                return JSONResponse(error=str(e))

            if data["user"] and not request.user.owner:
                return JSONResponse(error="Unauthorized", status_code=401)

            user = self.auth_manager.get_user(data["user"]) or request.user

            provider: CredentialProvider = (
                self.auth_manager.credential_providers[data["provider"]])

            creds, return_data = await provider.create_credentials(
                user, data["data"])
            self.auth_manager.users.schedule_save()

            return JSONResponse({
                "credential_id": creds.credential_id,
                "data": return_data
            })

        @router.post("/auth/create_user")
        @needs_auth(owner_only=True, log_invalid=True)
        async def create_user(request: web.Request) -> JSONResponse:
            """Creates a user"""
            payload_schema = vol.Schema({
                vol.Required("name"): str,
                vol.Required("password"): str,
                vol.Optional("is_owner", default=False): bool,
            })
            payload = payload_schema(await request.json())

            user = await self.auth_manager.create_user(
                name=payload["name"],
                owner=payload["is_owner"]
            )

            provider: CredentialProvider = (
                self.auth_manager.credential_providers["password"])

            await provider.create_credentials(user, payload["password"])

            self.auth_manager.users.schedule_save()

            return JSONResponse({
                "user_id": user.id
            })

        @router.post("/auth/token")
        async def auth_token(request: web.Request) -> JSONResponse:
            """The OAuth2 /token endpoint"""
            try:
                data = dict((await request.post()).items())
                payload = TOKEN_PAYLOAD_SCHEMA(data)
            except vol.Invalid as e:
                path = ', '.join([str(var) for var in e.path])
                return JSONResponse({
                    "error": "invalid_request",
                    "error_description": "Invalid parameters: "
                                         f"{path}"
                }, status_code=400)

            if payload["grant_type"] == "code":
                try:
                    payload = AUTH_CODE_SCHEMA(payload)
                except vol.Invalid:
                    return JSONResponse({
                        "error": "invalid_grant",
                        "error_description": "Invalid authorization code"
                    }, status_code=400)

                code = self.auth_manager.auth_codes.get(payload["code"])
                if not code:
                    return JSONResponse({
                        "error": "invalid_grant",
                        "error_description": "Invalid authorization code"
                    }, status_code=400)

                if code.expired:
                    return JSONResponse({
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
                    return JSONResponse({
                        "error": "invalid_grant",
                        "error_description": "Invalid credentials"
                    }, status_code=400)

                cred_provider: CredentialProvider = (
                    self.auth_manager.credential_providers["password"])

                user = self.auth_manager.get_user_by_name(payload["username"])

                login_valid = await cred_provider.validate_login_data(
                    user,
                    payload["password"]
                )

                if not login_valid:
                    return JSONResponse({
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
                        return JSONResponse({
                            "error": "invalid_grant",
                            "error_description": "Grant type 'refresh_token'"
                                                 "needs a 'refresh_token'"
                                                 "parameter"
                        }, status_code=400)
                    return JSONResponse(
                        {
                            "error": "invalid_request",
                            "error_description": "Invalid parameters: "
                                                 f"{', '.join(e.path)}"
                        }, status_code=400)

                refresh_token = self.auth_manager.get_refresh_token_by_string(
                    payload["refresh_token"]
                )

                if not refresh_token:
                    return JSONResponse({
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
