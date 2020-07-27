"""Exceptions"""


class HomeControlException(Exception):
    """The base exception for HomeControl"""


class ItemNotFoundException(HomeControlException):
    """Item not found"""


class ModuleNotFoundException(HomeControlException):
    """Module not found"""


class PipInstallError(HomeControlException):
    """A pip install failed"""


class ConfigDomainAlreadyRegistered(HomeControlException):
    """The configuration domain is already registered"""


class ConfigurationNotApproved(HomeControlException):
    """Configuration has not been approved"""


class ItemNotOnlineError(HomeControlException):
    """Item is not online"""


class ItemTypeNotExistsError(HomeControlException):
    """Item type does not exist"""
