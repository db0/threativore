import random
import uuid

import regex as re

from threativore.flask import SQLITE_MODE

random.seed(random.SystemRandom().randint(0, 2**32 - 1))


def get_db_uuid() -> str | uuid.UUID:
    if SQLITE_MODE:
        return str(uuid.uuid4())
    return uuid.uuid4()


def validate_regex(regex: str) -> bool:
    try:
        re.compile(regex, re.IGNORECASE)
    except Exception:
        return False
    return True


def is_valid_user_url(user_url: str) -> bool:
    return re.search(r"^https?://.+?/u/.+$", user_url) is not None
