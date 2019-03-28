import voluptuous as vol


MINIMUM_PYTHON_VERSION = (3, 6, 5)

EXIT_SHUTDOWN = 0
EXIT_RESTART = 1

WORKING = "working"
NOT_WORKING = "not_working"
STOPPED = "stopped"

SCHEMA_MODULE_MANAGER = vol.Schema({
    vol.Required("folders", default=[]): [str]
})

SCHEMA_CONFIG = vol.Schema({
    vol.Required("module-manager", default=SCHEMA_MODULE_MANAGER({})): SCHEMA_MODULE_MANAGER,
}, extra=vol.ALLOW_EXTRA)
