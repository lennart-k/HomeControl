"""config_manager module"""

import logging
import os
from collections import defaultdict
from typing import Any, Optional

import voluptuous as vol
from homecontrol.dependencies.yaml_loader import YAMLLoader
from homecontrol.exceptions import (ConfigDomainAlreadyRegistered)

LOGGER = logging.getLogger(__name__)


class ConfigManager:
    """
    ConfigManager

    Manages the configuration with configuration domains
    """

    def __init__(self, cfg: dict, cfg_path: str) -> None:
        self.cfg = cfg
        self.cfg_path = cfg_path
        self.domains = {}
        self.domain_schemas = {}

    def get(self, key, default=None):
        """getter for self.cfg"""
        return self.cfg.get(key, default)

    def __getitem__(self, key):
        return self.cfg[key]

    async def reload_config(self, only_domain: Optional[str] = None) -> None:
        """Reloads the configuration and updates where it can"""
        cfg = YAMLLoader.load(
            open(self.cfg_path), cfg_folder=os.path.dirname(self.cfg_path))

        LOGGER.info("Reloading the configuration")
        for domain, raw_domain_config in cfg.items():
            if only_domain and domain != only_domain:
                continue
            if raw_domain_config != self.cfg.get(domain, None):
                LOGGER.info("New configuration detected for domain %s", domain)

                if not self.domains.get(domain):
                    LOGGER.warning(
                        "Configuration domain %s is not reloadable", domain)
                    continue
                try:
                    domain_config = self.validate_domain_config(
                        domain, raw_domain_config)
                except vol.Error:
                    continue

                self.cfg[domain] = raw_domain_config

                if hasattr(self.domains.get(domain, None),
                           "apply_configuration"):
                    handler = self.domains[domain]
                    await handler.apply_configuration(
                        domain, domain_config)

                LOGGER.info("Configuration for domain %s updated", domain)

        LOGGER.info("Completed updating the configuration")

    def validate_domain_config(self,
                               domain: str,
                               config: dict) -> Any:
        """
        Validates a domain configuration
        """
        if domain in self.domain_schemas:  # Validate new configuration
            try:
                return self.domain_schemas[domain](config)
            except vol.Error as e:
                LOGGER.error(
                    "Configuration for domain %s is invalid",
                    domain,
                    exc_info=True)
                raise e

        return config

    async def register_domain(self,
                              domain: str,
                              handler: Optional[object] = None,
                              schema: Optional[vol.Schema] = None,
                              default: Optional[Any] = None) -> Any:
        """
        Registers a configuration domain
        """
        default = {} if default is None else default
        if domain in self.domains:
            raise ConfigDomainAlreadyRegistered(
                f"The configuration domain {domain} is already registered")

        self.domains[domain] = handler
        if schema:
            self.domain_schemas[domain] = schema

        return self.validate_domain_config(
            domain, self.cfg.get(domain, default))
