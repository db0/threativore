import regex as re
from loguru import logger
from sqlalchemy.exc import IntegrityError
import threativore.database as database
import threativore.exceptions as e
import threativore.utils as utils
from threativore.enums import UserRoleTypes
from threativore.flask import db
from threativore.orm.user import User
from threativore.config import Config
from threativore.emoji import lemmy_emoji


class ThreativoreUsers:
    def __init__(self, threativore):
        self.threativore = threativore

    def ensure_user_exists(self, user_url: str):
        user = database.get_user(user_url)
        if user:
            return user
        return self.create_user(user_url)

    def ensure_user_exists_with_role(self, user_url: str, role: UserRoleTypes):
        user = database.get_user(user_url)
        if user:
            self.add_role(user_url, role)
            return
        self.create_user(user_url, role)

    def create_user(self, user_url: str, role: UserRoleTypes = None, override=None) -> User:
        if not utils.is_valid_user_url(user_url):
            raise e.ReplyException(f"{user_url} not a valid fediverse ID")
        user = database.get_user(user_url)
        if user:
            logger.warning(f"{user_url} already exists")
            return user
        new_user = User(
            user_url=user_url,
            email_override=override
        )
        db.session.add(new_user)
        db.session.commit()
        if role:
            new_user.add_role(role)
        return new_user

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
        requesting_user = database.get_user(pm["creator"]["actor_id"].lower())
        if not requesting_user:
            raise e.ReplyException("Sorry, you do not have enough rights to do a users operation.")
        if not requesting_user.can_do_user_operations():
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
            if user_role == UserRoleTypes.TRUSTED and not requesting_user.can_create_trust():
                raise e.ReplyException("Sorry, you do not have enough rights to make users into TRUSTED.")
            self.ensure_user_exists_with_role(
                user_url=user_url,
                role=user_role,
            )
            self.threativore.reply_to_pm(
                pm=pm,
                message=(f"Role {user_role.name} has been succesfully added to {user_url} "),
            )
            logger.info(
                f"Role {user_role.name} has been succesfully added to {user_url} " f"from {requesting_user.user_url}",
            )
        else:
            roles_to_remove = [UserRoleTypes.MODERATOR, UserRoleTypes.TRUSTED, UserRoleTypes.KNOWN]
            if user_role_search:
                user_role = UserRoleTypes[user_role_search.group(1).upper()]
                if user_role == UserRoleTypes.ADMIN:
                    raise e.ReplyException("ADMIN role cannot be removed")
                if user_role == UserRoleTypes.MODERATOR and not requesting_user.can_create_mods():
                    raise e.ReplyException("Sorry, you do not have enough rights to remove users from MODERATOR.")
                roles_to_remove = [user_role]
            elif not requesting_user.can_create_mods():
                roles_to_remove = [UserRoleTypes.TRUSTED, UserRoleTypes.KNOWN]
            for role in roles_to_remove:
                self.remove_role(
                    user_url=user_url,
                    role=role,
                )
            self.threativore.reply_to_pm(
                pm=pm,
                message=(f"Roles {[r.name for r in roles_to_remove]} has been succesfully removed from {user_url} "),
            )
            logger.info(
                f"Roles {[r.name for r in roles_to_remove]} has been succesfully removed from {user_url} "
                f"from {requesting_user.user_url}",
            )

    def parse_override_pm(self, override_search, pm):
        # logger.info(pm['private_message']['content'])
        requesting_user = database.get_user(pm["creator"]["actor_id"].lower())
        if not requesting_user:
            requesting_user = self.ensure_user_exists(
                user_url=pm["creator"]["actor_id"].lower(),
            )
        override = override_search.group(1).strip().lower() if override_search.group(1).strip().lower() != '' else None
        if requesting_user.email_override != override:
            try:
                requesting_user.email_override = override
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                existing_user = database.get_user_from_override_email(override)
                logger.error(f"{requesting_user.user_url} tried to set override to {override} but it already exists on {existing_user.user_url}")
                raise e.ReplyException("Override already exists on someone else. Please contact the admins")
        if override is None:
            logger.info(
                f"Override has been succesfully removed from {requesting_user.user_url}",
            )
            self.threativore.reply_to_pm(
                pm=pm,
                message="Override has been succesfully removed",
            )
            return
        else:
            logger.info(
                f"Override has been succesfully set to {requesting_user.email_override} " 
                f"from {requesting_user.user_url}",
            )            
            self.threativore.reply_to_pm(
                pm=pm,
                message=(f"Override has been succesfully set to `{requesting_user.email_override}`"),
            )

    def parse_vouch_pm(self, vouch_search, pm):
        # logger.info(pm['private_message']['content'])
        requesting_user = database.get_user(pm["creator"]["actor_id"].lower())
        if not requesting_user:
            requesting_user = self.ensure_user_exists(
                user_url=pm["creator"]["actor_id"].lower(),
            )
        is_withdrawn = False
        if vouch_search.group(1):
            is_withdrawn = True
        target_user = vouch_search.group(2).strip().lower()
        if '@' not in target_user: target_user = f"{target_user}@{Config.lemmy_domain}"
        if requesting_user.user_url == utils.username_to_url(target_user):
            raise e.ReplyException("You cannot vouch for yourself, silly!")
        # TODO: Remove all vouches when trust is removed by admins
        if not requesting_user.is_trusted():
            raise e.ReplyException(
                "Sorry, you do not have enough rights to vouch for users. "
                "To vouch for others, you need to be in one of the following donation tiers: "
                f"{Config.trusted_tiers} "
                f"or have one of the following tags: {Config.trusted_tags}."
            )
        try:
            if self.threativore.lemmy.user.get(username=target_user) is None:
                raise e.ReplyException(f"user @{target_user} is not known to this instance. Please check your spelling and try again or contact the admins.")
        except Exception:
            raise e.ReplyException(f"user @{target_user} is not known to this instance. Please check your spelling and try again or contact the admins.")
        if not is_withdrawn and not requesting_user.is_moderator() and database.count_user_vouches(requesting_user.id) > Config.vouches_per_user:
            raise e.ReplyException(f"Sorry you have exceeded the maximum allowed vouches per user ({Config.vouches_per_user}). You cannot vouch for more users.")
        vouched_user = database.get_user(utils.username_to_url(target_user))
        if is_withdrawn:
            if not vouched_user:
                raise e.ReplyException(f"You attempted to withdraw your vouching for {target_user} but this vouch didn't exist.")
            existing_vouches = database.get_tag("vouched", vouched_user.id)
            if existing_vouches is None:
                raise e.ReplyException(f"You attempted to withdraw your vouching for {target_user} but this vouch didn't exist.")
            if existing_vouches.value != requesting_user.user_url:
                raise e.ReplyException(f"You attempted to withdraw your vouching for {target_user} someone else has vouched for this user instead.")
        elif vouched_user:
            existing_vouches = database.get_tag("vouched", vouched_user.id)
            if existing_vouches: 
                if existing_vouches.value != requesting_user.user_url:
                    raise e.ReplyException(f"You attempted to vouching for {target_user} but someone else has already vouched for them.")
                else:
                    raise e.ReplyException(f"You attempted to vouching for {target_user} but you have already vouched for the succesfully in the past.")
        if not vouched_user:
            vouched_user = self.threativore.users.ensure_user_exists(utils.username_to_url(target_user))
        if is_withdrawn:
            vouched_user.remove_tag("vouched")
            logger.info(
                f"{requesting_user.user_url} has succesfully removed vouch for {vouched_user.user_url}" 
            )            
            self.threativore.reply_to_pm(
                pm=pm,
                message=(f"You have succesfully withdrawn your vouch for {vouched_user.user_url}"),
            )
        else:
            emoji_markdown = lemmy_emoji.get_emoji_markdown("vouched")
            if emoji_markdown is None:
                emoji_markdown = ''
            vouched_user.set_tag(
                tag="vouched", 
                value=requesting_user.user_url,
            )        
            logger.info(
                f"{requesting_user.user_url} has succesfully vouched for {vouched_user.user_url}" 
            )            
            self.threativore.reply_to_pm(
                pm=pm,
                message=(f'You have succesfully {emoji_markdown}vouched{emoji_markdown} for {vouched_user.user_url}. That user has received a PM informing them of this.'),
            )
            self.threativore.reply_to_user_url(
                user_url=vouched_user.user_url,
                message=(f'Good News. Trusted user {requesting_user.user_url} has {emoji_markdown}vouched{emoji_markdown} for you as a valuable member of this instance.'),
            )
            