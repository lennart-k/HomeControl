"""WebSocket message class"""


class WebSocketMessage:
    """A class representing a WS message"""
    # pylint: disable=redefined-builtin,invalid-name
    __slots__ = ["type", "id", "data", "reply"]

    def __init__(self, data: dict) -> None:
        self.type = data["type"]
        self.id = data.get("id")
        self.data = data
        self.reply = data.get("reply")

    def success(self, data: object) -> dict:
        """Generates a success response"""
        return {
            "type": "reply",
            "id": self.id,
            "success": True,
            "data": data
        }

    def error(self, type: str, message: str) -> dict:
        """Generates an error response"""
        return {
            "type": "reply",
            "id": self.id,
            "success": False,
            "error": {
                "type": type,
                "message": message
            }
        }
