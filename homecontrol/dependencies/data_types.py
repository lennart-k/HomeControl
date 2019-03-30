import colorsys
from datetime import datetime

types = {}
type_set = set()


def data_type(cls: object) -> object:
    """
    Decorator to add a data type to the types dict
    """
    type_set.add(cls)
    types[cls.__name__] = cls
    return cls


@data_type
class Color:
    hsl: (int, int, int)

    def __init__(self, h: int, s: int, l: int):
        self.hsl = (h, s, l)

    @staticmethod
    def from_hsl(hsl: tuple):
        return Color(*hsl)

    @staticmethod
    def from_rgb(rgb: tuple):
        hls = colorsys.rgb_to_hls(*(i/255 for i in rgb))
        return Color(int(hls[0]*360), int(hls[2]*255), int(hls[1]*255))

    @staticmethod
    def from_data(rgb: tuple):
        return Color.from_rgb(rgb)

    @property
    def rgb(self) -> (int, int, int):
        return tuple(int(i*255) for i in colorsys.hls_to_rgb(self.hsl[0]/360, self.hsl[2]/255, self.hsl[1]/255))

    @rgb.setter
    def rgb(self, rgb: tuple):
        hls = colorsys.rgb_to_hls(*(i/255 for i in rgb))
        self.hsl = (int(hls[0]*360), int(hls[2]*255), int(hls[1]*255))

    @property
    def h(self) -> int:
        return self.hsl[0]

    @h.setter
    def h(self, h: int):
        hsl = list(self.hsl)
        hsl[0] = h
        self.hsl = hsl

    @property
    def s(self) -> int:
        return self.hsl[1]

    @s.setter
    def s(self, s: int):
        hsl = list(self.hsl)
        hsl[1] = s
        self.hsl = hsl

    @property
    def l(self) -> int:
        return self.hsl[2]

    @l.setter
    def l(self, l: int):
        hsl = list(self.hsl)
        hsl[2] = l
        self.hsl = hsl

    def dump(self) -> (int, int, int):
        return self.rgb

    
        


@data_type
class DateTime(datetime):
    @staticmethod
    def from_data(data):
        return DateTime.fromisoformat(*data)

    def dump(self):
        return self.isoformat()

