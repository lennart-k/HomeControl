class HomeControlException(BaseException):
    pass


class ItemNotFoundException(HomeControlException):
    pass

class ModuleNotFoundException(HomeControlException):
    pass

class NoCoreException(HomeControlException):
    pass

class InvalidConfigException(HomeControlException):
    pass

class TemplateErrorException(HomeControlException):
    pass

class ItemTypeNotFound(HomeControlException):
    pass
