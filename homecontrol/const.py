
MINIMUM_PYTHON_VERSION = (3, 6, 5)

EXIT_SHUTDOWN = 0
EXIT_RESTART = 1

WORKING = "working"
NOT_WORKING = "not_working"
STOPPED = "stopped"

ERROR404 = "error-404"
ERROR_ITEM_NOT_FOUND = "error-item-not-found"
ITEM_STATE_NOT_FOUND = "error-item-state-not-found"
ITEM_ACTION_NOT_FOUND = "error-item-action-not-found"
ERROR_INVALID_ITEM_STATES = "error-invalid-item-states"
ERROR_INVALID_ITEM_STATE = "error-invalid-item-state"

import voluptuous as vol

STATE_COMMIT_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

ITEM_SCHEMA = vol.Schema({
    vol.Optional("item_type"): str,
    vol.Required("id"): str,
    vol.Required("!type"): "Item"
})
MODULE_SCHEMA = vol.Schema({
    vol.Optional("meta"): str,
    vol.Required("name"): str,
    vol.Required("!type"): "Module"
})
