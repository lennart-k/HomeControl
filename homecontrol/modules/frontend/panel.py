"""A Frontend Panel"""
from typing import Optional


class Panel:
    """
    A Frontend panel
    """
    route: Optional[str]
    name: Optional[str]
    iframe: Optional[str]
    icon: Optional[str]
    provider: Optional[str]

    def __init__(self,
                 route: Optional[str] = None,
                 name: Optional[str] = None,
                 iframe: Optional[str] = None,
                 icon: Optional[str] = None,
                 provider: Optional[str] = None
                 ):

        self.route = route
        self.name = name or route
        self.iframe = iframe
        self.icon = icon
        self.provider = provider

    def to_dict(self) -> dict:
        """Returns a JSON-serialisable dictionary"""
        return {
            "name": self.name,
            "route": self.route,
            "iframe": self.iframe,
            "icon": self.icon,
            "provider": self.provider
        }
