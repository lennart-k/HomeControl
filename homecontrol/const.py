"""Constants used by HomeControl"""

from enum import Enum

VERSION = (0, 2, 0)
VERSION_STRING = ".".join(map(str, VERSION))


MINIMUM_PYTHON_VERSION = (3, 8, 0)

EXIT_SHUTDOWN = "EXIT_SHUTDOWN"
EXIT_RESTART = "EXIT_RESTART"

ERROR404 = "error-404"
ERROR_ITEM_NOT_FOUND = "error-item-not-found"
ITEM_STATE_NOT_FOUND = "error-item-state-not-found"
ITEM_ACTION_NOT_FOUND = "error-item-action-not-found"
ERROR_INVALID_ITEM_STATES = "error-invalid-item-states"
ERROR_INVALID_ITEM_STATE = "error-invalid-item-state"

EVENT_CORE_BOOTSTRAP_COMPLETE = "core_bootstrap_complete"
EVENT_ITEM_CREATED = "item_created"
EVENT_ITEM_REMOVED = "item_removed"
EVENT_ITEM_NOT_WORKING = "item_not_working"
EVENT_ITEM_STATUS_CHANGED = "item_status_changed"
EVENT_MODULE_LOADED = "module_loaded"

MAX_PENDING_WS_MSGS = 512

ATTRIBUTION = "attribution"


class ItemStatus(Enum):
    """Every status an item can have"""
    ONLINE = "online"
    OFFLINE = "offline"
    STOPPED = "stopped"
    WAITING_FOR_DEPENDENCY = "waiting-for-dependency"
