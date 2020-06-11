"""WebHooks for HomeControl"""

import json
from aiohttp import web

SPEC = {
    "name": "WebHooks",
    "description": "Provides WebHook endpoints"
}


class Module:
    """The WebHook module"""
    async def init(self):
        """Initialise the module"""

        @self.core.event_engine.register("http_add_api_routes")
        async def add_route(event, router):
            """Add an API route"""

            @router.get("/webhook/{target}")
            @router.post("/webhook/{target}")
            async def webhook_route(request):
                self.core.event_engine.broadcast(
                    "webhook_event",
                    target=request.match_info["target"], params={})
                return web.Response(
                    body=json.dumps(
                        {"msg": "Webhook triggered"},
                        indent=4, sort_keys=True),
                    content_type="application/json")

        @self.core.event_engine.register("gather_automation_providers")
        async def on_gather_automation_providers(event, engine, callback):
            """Register as an automation provider"""
            callback(trigger={"webhook": self.provider_factory})

    # pylint: disable=no-self-use
    def provider_factory(self, rule, engine):
        """Return a WebhookTriggerProvider for automation"""
        return WebhookTriggerProvider(rule, engine)


class WebhookTriggerProvider:
    """The trigger provider for automation"""

    def __init__(self, rule, engine):
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]
        self.event = self.data["target"]

        self.core.event_engine.register("webhook_event")(self.on_webhook)

    async def on_webhook(self, event, target, params):
        """Handle WebHook event"""
        if target == self.event:
            await self.rule.on_trigger(params)

    async def stop(self) -> None:
        """Stops the WebhookTriggerProvider"""
        self.core.event_engine.remove_handler("webhook_event", self.on_webhook)
