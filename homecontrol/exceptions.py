"""Exceptions"""

class HomeControlException(BaseException):
    """The base exception for HomeControl"""

class ItemNotFoundException(HomeControlException):
    """Item not found"""

class ModuleNotFoundException(HomeControlException):
    """Module not found"""

class NoCoreException(HomeControlException):
    """No core passed. Can for example be raised by yaml_loader when trying to construct an item"""

class InvalidConfigException(HomeControlException):
    """There's an error in the config directory"""

class PipInstallError(HomeControlException):
    """A pip install failed"""

class ItemTypeNotFound(HomeControlException):
    """There is no spec for the item type"""

class ConfigDomainAlreadyRegistered(HomeControlException):
    """The configuration domain is already registered"""

class ConfigurationNotApproved(HomeControlException):
    """Configuration has not been approved"""

class ItemNotOnlineError(HomeControlException):
    """Item is not online"""