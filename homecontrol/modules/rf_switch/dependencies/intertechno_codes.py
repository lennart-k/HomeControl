HOUSES = "abcdefghijklmnop"


def from_code(code: int) -> (str, int, bool):
    b = "{0:0>12}".format(bin(code)[2:])
    house = HOUSES[int(b[0:4][::-1], 2)]
    id = int(b[4:8:][::-1], 2)+1
    check = b[8:10] == "01"
    state = {"11": True, "10": False}.get(b[10:12], None)
    if check:
        return house, id, state
    else:
        return False


def to_code(house: str, id: int, state: bool) -> int:
    h = bin(HOUSES.index(house.lower()))[2:][::-1]
    i = bin(id-1)[2:][::-1]
    state = "11" if state else "10"
    return int(h+i+"01"+state, 2)


if __name__ == "__main__":
    code = 3383
    it_code = from_code(code)
    print(bin(code)[2:])
    print(it_code)
    print(to_code(*it_code))
