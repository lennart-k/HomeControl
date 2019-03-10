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
    r: int
    g: int
    b: int

    def __init__(self, r, g, b):
        self.r, self.g, self.b = r, g, b

    @staticmethod
    def from_data(data):
        return Color(*data)

    def dump(self):
        return self.r, self.g, self.b

    @staticmethod
    def validate(*args, rule_spec=None):
        if len(args) == 3 and all(type(i) == int for i in args):
            return max(*args) <= 255 and min(*args) >= 0
        return False

    def to_tuple(self):
        return self.r, self.g, self.b


@data_type
class DateTime(datetime):
    @staticmethod
    def from_data(data):
        return DateTime.fromisoformat(*data)

    def dump(self):
        return self.isoformat()
