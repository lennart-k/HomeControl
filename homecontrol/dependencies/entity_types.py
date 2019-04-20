class Item:
    def __repr__(self) -> str:
        return f"<Item {self.type} identifier={self.identifier} name={self.name}>"


class Module:
    def __repr__(self) -> str:
        return f"<Module {self.name}>"
