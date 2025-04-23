from typing import Any

import regex as re
from loguru import logger

import threativore.database as database
import threativore.exceptions as e
from threativore.enums import UserRoleTypes
from threativore.orm.keystore import KeyStore

class ThreativoreFediseerActions:
    threativore = None
    
    def __init__(self, threativore):
        self.threativore = threativore

    def parse_blocklist_pm(self, blocklist_search, pm):
        user_url = pm["creator"]["actor_id"].lower()
        user = database.get_user(user_url)
        if not user:
            raise e.ThreativoreException(f"{user_url} not known")
        if not user.has_role(UserRoleTypes.ADMIN) and not user.has_role(UserRoleTypes.MODERATOR):
            raise e.ThreativoreException(f"{user_url} doesn't have enough privileges to action appeals")
        validating_blocklist = KeyStore.get_validating_blocklist()
        if not validating_blocklist:
            raise e.ReplyException("There is currently no validating blocklist waiting for approval.")
        self.threativore.lemmy.private_message.mark_as_read(pm["private_message"]["id"], True)
        if blocklist_search.group(1) == "approve":
            self.threativore.fediseer.apply_blocklist(validating_blocklist)
        else:
            self.threativore.fediseer.reject_blocklist(validating_blocklist)
