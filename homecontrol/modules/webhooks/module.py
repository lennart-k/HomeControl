import json
from aiohttp import web

class Module:
    async def init(self):

        @event("add_api_routes")
        async def add_route(event, router):

            @router.get("/webhook/{target}")
            async def gassist(request):
                self.core.event_engine.broadcast("webhook_event", target=request.match_info["target"], params={})
                return web.Response(body=json.dumps({"msg": "Webhook triggered"}, indent=4, sort_keys=True),
                content_type="application/json")

        @event("gather_automation_providers")
        async def on_gather_automation_providers(event, engine, callback):
            callback(trigger={"webhook": self.provider_factory})

    def provider_factory(self, rule, engine):
        return WebhookTriggerProvider(rule, engine)


class WebhookTriggerProvider:
    def __init__(self, rule, engine):
        self.rule = rule
        self.engine = engine
        self.core = engine.core

        self.data = rule.data["trigger"]
        self.event = self.data["target"]

        @event("webhook_event")
        async def on_webhook(event, target, params):
            if target == self.event:
                await self.rule.on_trigger(params)