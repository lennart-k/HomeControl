from dependencies import json
from aiohttp import web

class JSONResponse(web.Response):
    def __init__(self, data=None, error=None, status_code: int = 200, core=None, headers=None):
        response = {
            "success": not error,
            **({"error": error} if error else {}),
            "status_code": status_code,
            **({"data": data} if not error else {})
        }
        super().__init__(body=json.dumps(response, indent=4, sort_keys=True, core=core),
                         status=status_code, content_type="application/json",
                         charset="utf-8", headers=headers)
