from aiohttp import web

class Module:
    async def init(self):
        print("ACTIONS ON GOOGLE!")

        @event("add_api_routes")
        async def add_route(event, router):
            print("GOOGLE ASSISTANT", router)

            @router.get("/gassist")
            async def gassist(request):
                return web.Response()