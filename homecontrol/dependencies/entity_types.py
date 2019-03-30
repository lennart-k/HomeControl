class Item:
    def __repr__(self) -> str:
        return f"<Item {self.type} {self.identifier}>"


class Module:
    def __repr__(self) -> str:
        return f"<Module {self.name}>"
