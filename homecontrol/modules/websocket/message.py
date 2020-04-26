"""WebSocket message class"""


class WebSocketMessage:
    """A class representing a WS message"""
    # pylint: disable=redefined-builtin,invalid-name
    __slots__ = ["type", "id", "data", "reply"]

    def __init__(self, type: str, id: str = None,
                 data: object = None, reply: bool = True) -> None:
        self.type = type
        self.id = id
        self.data = data
        self.reply = reply

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
