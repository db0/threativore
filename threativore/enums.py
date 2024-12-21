import enum


class UserRoleTypes(enum.Enum):
    ADMIN = 0
    # Can add Trusted Users and Filters
    MODERATOR = 1
    # Reports from this user are treated as trustrworthy
    TRUSTED = 2
    # Their posts are not triggering the spam filter
    KNOWN = 3


class FilterAction(enum.Enum):
    PERMABAN = 0
    BAN30 = 1
    BAN7 = 2
    REPORT = 3
    REMOVE = 4
    REMBAN = 5


class FilterType(enum.Enum):
    REPORT = 0
    COMMENT = 1
    URL = 2
    USERNAME = 3


class EntityType(enum.Enum):
    COMMENT = 0
    POST = 1
    REPORT = 2

class AppealStatus(enum.Enum):
    PENDING = 0
    RESTORED = 1
    REJECTED = 2
