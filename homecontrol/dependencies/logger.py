class Logger:
    def __init__(self, core):
        self.core = core

        event = self.core.event_engine.register

        @event("state_change")
        async def on_state_change(event, item, changes):
            print(f"STATE CHANGE:\t\t{item.identifier}\t{changes}")

        @event("item_created")
        async def on_item_created(event, item):
            print(f"ITEM CREATED:\t\t{item.type}\t{item.identifier}")

        # @event("entity_discovered")
        async def on_entity_discovered(event, d_type, d_info):
            print(f"ENTITY DISCOVERED:\t{d_type}\t\t{d_info}")

    def info(self, *args: str):
        pass

    def warn(self, *args: str):
        pass

    def error(self, *args: str):
        pass

    def debug(self, *args: str):
        pass