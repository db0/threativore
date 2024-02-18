import enum


class UserRoleTypes(enum.Enum):
    ADMIN = 0
    MODERATOR = 1
    TRUSTED = 2


class FilterAction(enum.Enum):
    PERMABAN = 0
    BAN30 = 1
    BAN7 = 2
    REPORT = 3
    REMOVE = 4


class FilterType(enum.Enum):
    REPORT = 0
    COMMENT = 1
    URL = 2
    USERNAME = 3


class EntityType(enum.Enum):
    COMMENT = 0
    POST = 1
    REPORT = 2
