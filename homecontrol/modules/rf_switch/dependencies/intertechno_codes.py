"""Translate between Intertechno RF codes and what they mean"""

HOUSES = "abcdefghijklmnop"


# pylint: disable=invalid-name
def from_code(code: int) -> (str, int, bool):
    """Convert RF code to data"""
    b = "{0:0>12}".format(bin(code)[2:])
    house = HOUSES[int(b[0:4][::-1], 2)]
    identifier = int(b[4:8:][::-1], 2)+1
    check = b[8:10] == "01"
    state = {"11": True, "10": False}.get(b[10:12], None)
    if check:
        return house, identifier, state
    return False


def to_code(house: str, identifier: int, state: bool) -> int:
    """Generate an RF code"""
    h = bin(HOUSES.index(house.lower()))[2:][::-1]
    i = bin(identifier-1)[2:][::-1]
    state = "11" if state else "10"
    return int(h+i+"01"+state, 2)
