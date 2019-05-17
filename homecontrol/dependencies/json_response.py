"""JSONResponse module"""

from typing import Any
from aiohttp import web
from homecontrol.dependencies import json


# pylint: disable=too-many-ancestors,too-many-arguments,too-few-public-methods
class JSONResponse(web.Response):
    """A HTTP response for JSON data"""
    def __init__(self,
                 data: Any = None,
                 error: Exception = None,
                 status_code: int = 200,
                 core: "homecontrol.core.Core" = None,
                 headers: dict = None):
        response = {
            "success": not error,
            **({"error": error} if error else {}),
            "status_code": status_code,
            **({"data": data} if not error else {})
        }
        super().__init__(body=json.dumps(response, indent=4, sort_keys=True, core=core),
                         status=status_code, content_type="application/json",
                         charset="utf-8", headers=headers)
