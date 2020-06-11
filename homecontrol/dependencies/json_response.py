"""JSONResponse module"""

from typing import Any

from aiohttp import web

from homecontrol.dependencies import json


# pylint: disable=too-many-ancestors,too-many-arguments,too-few-public-methods
class JSONResponse(web.Response):
    """A HTTP response for JSON data"""

    def __init__(
            self,
            data: Any = None,
            error: str = None,
            status_code: int = 200,
            core=None,
            headers: dict = None) -> None:

        response = {"error": error} if error else data

        super().__init__(body=json.dumps(response, indent=4, sort_keys=True,
                                         core=core),
                         status=status_code, content_type="application/json",
                         charset="utf-8", headers=headers)
