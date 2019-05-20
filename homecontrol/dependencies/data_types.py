"""data types for HomeControl that can be translated to JSON for API usage"""

import colorsys
from datetime import datetime

# pylint: disable=invalid-name
types = {}
type_set = set()


def data_type(cls: object) -> object:
    """Decorator to add a data type to the types dict"""
    type_set.add(cls)
    types[cls.__name__] = cls
    return cls


@data_type
class Color:
    """Representation for a color"""
    hsl: (int, int, int)

    def __init__(self, h: int, s: int, l: int):
        self.hsl = (h, s, l)

    def __repr__(self) -> str:
        return f"<Color rgb={self.rgb} hsl={self.hsl}>"

    @staticmethod
    def from_hsl(hsl: tuple):
        """HSL constructor"""
        return Color(*hsl)

    @staticmethod
    def from_rgb(rgb: tuple):
        """RGB constructor"""
        hls = colorsys.rgb_to_hls(*(i / 255 for i in rgb))
        return Color(int(hls[0] * 360), int(hls[2] * 255), int(hls[1] * 255))

    @staticmethod
    def from_data(hsl: tuple):
        """
        Constructor from the data received through the API or configuration
        """
        return Color.from_hsl(hsl)

    @property
    def rgb(self) -> (int, int, int):
        """RGB"""
        return tuple(int(i * 255) for i in
                     colorsys.hls_to_rgb(
                         self.hsl[0] / 360,
                         self.hsl[2] / 255,
                         self.hsl[1] / 255))

    @rgb.setter
    def rgb(self, rgb: tuple):
        hls = colorsys.rgb_to_hls(*(i / 255 for i in rgb))
        self.hsl = (int(hls[0] * 360), int(hls[2] * 255), int(hls[1] * 255))

    @property
    def h(self) -> int:
        """Hue"""
        return self.hsl[0]

    @h.setter
    def h(self, h: int):
        hsl = list(self.hsl)
        hsl[0] = h
        self.hsl = hsl

    @property
    def s(self) -> int:
        """Saturation"""
        return self.hsl[1]

    @s.setter
    def s(self, s: int):
        hsl = list(self.hsl)
        hsl[1] = s
        self.hsl = hsl

    @property
    def l(self) -> int:
        """Lightness"""
        return self.hsl[2]

    @l.setter
    def l(self, l: int):
        hsl = list(self.hsl)
        hsl[2] = l
        self.hsl = hsl

    def dump(self) -> (int, int, int):
        """Dumps the Color into a JSON serialisable format"""
        return self.hsl


@data_type
class DateTime(datetime):
    """date time format"""
    @staticmethod
    def from_data(data):
        """Construct from JSON serialisable data"""
        return DateTime.fromisoformat(*data)

    def dump(self):
        """Dump to JSON serialisable data"""
        return self.isoformat()
