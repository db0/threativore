import random
import uuid

import regex as re

from threativore.flask import SQLITE_MODE
from threativore import exceptions as e

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

def regex_user_url(user_url: str) -> bool:
    return re.search(r"^https?://(.+?)/u/(.+)$", user_url)

def is_valid_user_url(user_url: str) -> bool:
    return regex_user_url(user_url) is not None


def username_to_url(user_id: str) -> str:
    if '@' not in user_id:
        raise e.BadRequest(f"{user_id} not a valid user ID")
    if user_id.startswith('@'):
        user_id = user_id[1:]
    user_split = user_id.lower().split("@",2)
    return f"https://{user_split[1]}/u/{user_split[0]}"


def url_to_username(user_url: str) -> str:
    uregex = regex_user_url(user_url)
    if uregex is None:
        raise e.BadRequest(f"{user_url} not a valid user URL")
    return f"{uregex.group(2)}@{uregex.group(1)}"
