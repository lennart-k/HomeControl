import asyncio
from netdisco.discovery import NetworkDiscovery
from concurrent.futures import ThreadPoolExecutor


class EntityDiscoveryProvider:
    def __init__(self, core):
        self.core = core
        self.net_disco = NetworkDiscovery()
        self.available_devices = set()
        self.active = self.core.cfg.get("entity-discovery", {}).get("active")
        self.interval = self.core.cfg.get("entity-discovery", {}).get("interval", 30)
