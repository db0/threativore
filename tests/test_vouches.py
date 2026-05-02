import regex as re
import time
from threativore.main import threativore
from threativore.enums import UserRoleTypes
from threativore.flask import APP
from threativore.enums import FilterAction, FilterType
from loguru import logger
import threativore.database as database
from threativore.orm.user import User, UserRole, UserTag, UserAlias

@logger.catch
def test_vouches():
    with APP.app_context():
        user = database.get_user("https://lemmy.dbzer0.com/u/db0")
        print([user.user_url, user.id])
        logger.info(database.count_user_vouches(user.user_url))
        logger.info(database.count_user_vouches_in_past_month(user.user_url))
        pass

test_vouches()