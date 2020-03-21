""""API endpoints"""

from collections import ChainMap
from json import JSONDecodeError
import voluptuous as vol
from aiohttp import web
from homecontrol.const import (
    ERROR_ITEM_NOT_FOUND,
    ITEM_STATE_NOT_FOUND,
    ITEM_ACTION_NOT_FOUND,
    ERROR_INVALID_ITEM_STATES,
    ERROR_INVALID_ITEM_STATE,
    ItemStatus
)
from homecontrol.modules.auth.decorator import needs_auth
from homecontrol.dependencies.json_response import JSONResponse
import json
from homecontrol.exceptions import ItemNotOnlineError

from .view import APIView


CONFIG_SCHEMA = vol.Schema({
    vol.Required("headers", default={}): {vol.Coerce(str): vol.Coerce(str)}
})
STATE_COMMIT_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)


def add_routes(app: web.Application):
    """
    Adds the views from this module
    """
    ActionsView.register_view(app)
    PingView.register_view(app)
    CoreShutdownView.register_view(app)
    CoreRestartView.register_view(app)
    ReloadConfigView.register_view(app)
    ListItemsView.register_view(app)
    GetItemView.register_view(app)
    ItemStatesView.register_view(app)
    ItemStateView.register_view(app)
    ActionsView.register_view(app)
    ExecuteActionView.register_view(app)


class PingView(APIView):
    """Ping view"""
    path = "/ping"

    async def get(self) -> JSONResponse:
        """Handle /ping"""
        return self.json("PONG")


@needs_auth(owner_only=True)
class CoreShutdownView(APIView):
    """Handle /core/shutdown"""
    path = "/core/shutdown"

    async def post(self) -> JSONResponse:
        """POST /core/shutdown"""
        self.core.loop.call_soon(self.core.shutdown)
        return self.json("Shutting down")


@needs_auth(owner_only=True)
class CoreRestartView(APIView):
    """Handle /core/restart"""
    path = "/core/restart"

    async def post(self) -> JSONResponse:
        """POST /core/restart"""
        self.core.loop.call_soon(self.core.restart)
        return self.json("Restarting")


@needs_auth(owner_only=True)
class ReloadConfigView(APIView):
    """Reloads the configuration"""
    path = "/core/config/reload"

    async def post(self) -> JSONResponse:
        """POST /core/config/reload"""
        await self.core.cfg.reload_config()
        return self.json("Reloaded configuration")


@needs_auth()
class ListItemsView(APIView):
    """Lists the items"""
    path = "/items"

    async def get(self) -> JSONResponse:
        """"GET /items"""
        return self.json([
            {
                "id": item.identifier,
                "name": item.name,
                "type": item.type,
                "module": item.module.name,
                "status": item.status.value,
                "actions": list(item.actions.actions.keys()),
                "states": await item.states.dump()
            } for item in self.core.item_manager.items.values()
        ])


@needs_auth()
class GetItemView(APIView):
    """Returns information about an item"""
    path = "/item/{id}"

    async def get(self) -> JSONResponse:
        """GET /item/{id}"""
        identifier = self.data["id"]
        item = self.core.item_manager.items.get(identifier)

        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", 404)

        return self.json({
            "id": item.identifier,
            "type": item.type,
            "module": item.module.name,
            "config": item.cfg,
            "status": item.status.value
        })


@needs_auth()
class ItemStatesView(APIView):
    """Item states view"""
    path = "/item/{id}/states"

    async def get(self) -> JSONResponse:
        """GET /item/{id}/states"""
        identifier = self.data["id"]
        item = self.core.item_manager.items.get(identifier)

        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", 404)

        return self.json({
            "item": item,
            "type": item.type,
            "states": await item.states.dump(),
        })

    async def post(self) -> JSONResponse:
        """POST /item/{id}/states"""
        identifier = self.data["id"]
        item = self.core.item_manager.items.get(identifier)

        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", 404)

        try:
            content = (await self.request.content.read()).decode()
            commit = STATE_COMMIT_SCHEMA(
                json.loads(content) if content else {})
        # pylint: disable=broad-except
        except Exception as e:
            return JSONResponse(error=e)

        if not commit.keys() & item.states.states.keys() == commit.keys():
            return self.error(
                ERROR_INVALID_ITEM_STATES,
                f"The given states {set(commit.keys())} do not comply with "
                f"accepted states {set(item.states.states.keys())}")

        if not item.status == ItemStatus.ONLINE:
            return JSONResponse(
                error=ItemNotOnlineError(
                    f"The item {item.identifier} is not online"))

        return JSONResponse(dict(ChainMap(
            *[await item.states.set(state, value)
              for state, value in commit.items()])))



@needs_auth()
class ItemStateView(APIView):
    """Endpoint for an item state"""
    path = "/item/{id}/states/{state_name}"

    async def post(self) -> JSONResponse:
        """POST /item/{id}/states/{state_name}"""
        identifier = self.data["id"]
        state_name = self.data["state_name"]
        item = self.core.item_manager.items.get(identifier)

        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", 404)

        if state_name not in item.states.states.keys():
            return self.error(
                ERROR_INVALID_ITEM_STATE,
                f"The given state '{state_name}' does not exist")

        if not item.status == ItemStatus.ONLINE:
            return self.error(ItemNotOnlineError(
                f"The item {item.identifier} is not online"))

        try:
            content = (await self.request.content.read()).decode()
            value = json.loads(content) if content else {}
            result = await item.states.set(state_name, value)
        # pylint: disable=broad-except
        except (Exception, vol.error.Error) as e:
            return self.error(e)

        return self.json(result)

    async def get(self) -> JSONResponse:
        """GET /item/{id}/states/{state_name}"""
        identifier = self.data["id"]
        state_name = self.data["state_name"]
        item = self.core.item_manager.items.get(identifier)

        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", 404)

        if state_name not in item.states.states:
            return self.error(
                ITEM_STATE_NOT_FOUND,
                f"Couldn't get state {state_name} from item {identifier}")

        return self.json({
            "item": item,
            "type": item.type,
            "states": {
                state_name: await item.states.get(state_name)
            }
        })


@needs_auth()
class ActionsView(APIView):
    """View item actions"""
    path = "/item/{id}/actions"

    async def get(self):
        """
        Get an item's actions
        """
        identifier = self.data["id"]
        item = self.core.item_manager.items.get(identifier)
        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", status_code=404)

        return self.json(data=list(item.actions.actions.keys()))


@needs_auth()
class ExecuteActionView(APIView):
    """Executes an action"""
    path = "/item/{id}/action/{action_name}"

    async def post(self) -> JSONResponse:
        """
        Executes an item's action and returns a boolean indicating the
        success of the action.
        """

        identifier = self.data["id"]
        action_name = self.data["action_name"]
        item = self.core.item_manager.items.get(identifier)
        if not item:
            return self.error(
                ERROR_ITEM_NOT_FOUND,
                f"No item found with identifier {identifier}", status_code=404)

        try:
            content = (await self.request.content.read()).decode()
            kwargs = json.loads(content) if content else {}
        except JSONDecodeError as e:
            return self.error(e)

        if action_name not in item.actions.actions:
            return self.error(
                ITEM_ACTION_NOT_FOUND,
                f"Item {identifier} of type {item.type} "
                f"does not have an action {action_name}")

        try:
            return self.json({
                "item": item,
                "action": action_name,
                "result": await item.actions.execute(action_name, **kwargs)
            })
        # pylint: disable=broad-except
        except Exception as e:
            return self.error(e)

    get = post
