import regex as re
from loguru import logger

import threagetarian.database as database
import threagetarian.exceptions as e
import threagetarian.utils as utils
from threagetarian.enums import UserRoleTypes
from threagetarian.flask import db
from threagetarian.orm.user import User


class ThreagetarianUsers:
    def __init__(self, lemmy):
        self.lemmy = lemmy

    def ensure_user_exists_with_role(self, user_url: str, role: UserRoleTypes):
        user = database.get_user(user_url)
        if user:
            self.add_role(user_url, role)
            return
        self.create_user(user_url, role)

    def create_user(self, user_url: str, role: UserRoleTypes = None):
        if not utils.is_valid_user_url(user_url):
            raise e.ReplyException(f"{user_url} not a valid fediverse ID")
        user = database.get_user(user_url)
        if user:
            logger.warning(f"{user_url} already exists")
            return
        new_user = User(
            user_url=user_url,
        )
        db.session.add(new_user)
        db.session.commit()
        if role:
            new_user.add_role(role)

    def add_role(self, user_url: str, role: UserRoleTypes):
        user = database.get_user(user_url)
        if not user:
            logger.warning(f"{user_url} doesn't exist")
            return
        user.add_role(role)

    def remove_role(self, user_url: str, role: UserRoleTypes):
        user = database.get_user(user_url)
        if not user:
            logger.warning(f"{user_url} doesn't exist")
            return
        user.remove_role(role)

    def parse_user_pm(self, user_search, pm):
        # logger.info(pm['private_message']['content'])
        requesting_user = database.get_user(pm["creator"]["actor_id"])
        if not requesting_user:
            raise e.ReplyException("Sorry, you do not have enough rights to do a users operation.")
        user_method = user_search.group(1).lower()
        user_url = user_search.group(2).strip().lower()
        if not utils.is_valid_user_url(user_url):
            user_search = re.search(r"\[.*\]\((https?://.*)\)[ \n]*?", pm["private_message"]["content"], re.IGNORECASE)
            user_url_retry = user_search.group(1).strip().lower()
            if not utils.is_valid_user_url(user_url_retry):
                raise e.ReplyException(
                    f"No valid user URL found in PM: {user_url}\n\n"
                    "To ensure mod rights are added correctly, please send the user account URL.",
                )
            user_url = user_url_retry
        ur_values = "|".join([e.name for e in UserRoleTypes])
        user_role_search = re.search(rf"role: ?`({ur_values})`?", pm["private_message"]["content"], re.IGNORECASE)
        if user_method == "add":
            if not user_role_search:
                raise e.ReplyException("Role required when adding user")
            user_role = UserRoleTypes[user_role_search.group(1).upper()]
            if user_role == UserRoleTypes.ADMIN:
                raise e.ReplyException("ADMIN role cannot be assigned")
            if user_role == UserRoleTypes.MODERATOR and not requesting_user.can_create_mods():
                raise e.ReplyException("Sorry, you do not have enough rights to make users into MODERATOR.")
            self.ensure_user_exists_with_role(
                user_url=user_url,
                role=user_role,
            )
            self.reply_to_pm(
                pm=pm,
                message=(f"Role {user_role.name} has been succesfully added to {user_url} "),
            )
            logger.info(
                f"Role {user_role.name} has been succesfully added to {user_url} " f"from {requesting_user.user_url}",
            )
        else:
            roles_to_remove = [UserRoleTypes.MODERATOR, UserRoleTypes.TRUSTED]
            if user_role_search:
                user_role = UserRoleTypes[user_role_search.group(1).upper()]
                if user_role == UserRoleTypes.ADMIN:
                    raise e.ReplyException("ADMIN role cannot be removed")
                if user_role == UserRoleTypes.MODERATOR and not requesting_user.can_create_mods():
                    raise e.ReplyException("Sorry, you do not have enough rights to remove users from MODERATOR.")
                roles_to_remove = [user_role]
            elif not requesting_user.can_create_mods():
                roles_to_remove = [UserRoleTypes.TRUSTED]
            for role in roles_to_remove:
                self.remove_role(
                    user_url=user_url,
                    role=role,
                )
            self.reply_to_pm(
                pm=pm,
                message=(f"Roles {[r.name for r in roles_to_remove]} has been succesfully removed from {user_url} "),
            )
            logger.info(
                f"Roles {[r.name for r in roles_to_remove]} has been succesfully removed from {user_url} "
                f"from {requesting_user.user_url}",
            )
