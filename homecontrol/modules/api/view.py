"""The API view module"""
from typing import Any, Union
from aiohttp import web
from homecontrol.core import Core
from homecontrol.dependencies.json_response import JSONResponse


class APIView(web.View):
    """
    An API view
    """
    core: Core
    path: str

    def __init__(self, request):
        self.app = request.app
        self.core = self.app["core"]
        self.data = request.match_info
        super().__init__(request)

    @classmethod
    def register_view(cls, app: web.Application):
        """Registers the view to a router"""
        assert cls.path
        app.router.add_view(cls.path, cls)

    def json(
            self, data: Any = None, status_code: int = 200,
            headers: dict = None) -> JSONResponse:
        """Creates a JSONResponse"""
        return JSONResponse(
            data, status_code=status_code, core=self.core, headers=headers)

    def error(
            self, error: Union[str, Exception],
            message: str = None, status_code: int = 500) -> JSONResponse:
        """Creates an error message"""
        return JSONResponse(
            error={
                "type": type(error).__name__,
                "message": str(error)
            } if isinstance(error, Exception) else {
                "type": error,
                "message": message
            }, status_code=status_code
        )
