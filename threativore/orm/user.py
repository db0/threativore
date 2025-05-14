from datetime import datetime, timedelta

from sqlalchemy import Enum, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID

import threativore.exceptions as e
from threativore.enums import UserRoleTypes
from threativore.flask import db
from threativore.emoji import lemmy_emoji
from threativore.config import Config
from loguru import logger
uuid_column_type = lambda: UUID(as_uuid=True) if not Config.use_sqlite else db.String(36)  # FIXME # noqa E731


class UserRole(db.Model):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "user_role", name="user_id_role"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship("User", back_populates="roles")
    user_role = db.Column(Enum(UserRoleTypes), nullable=False)
    value = db.Column(db.Boolean, default=False, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Define event listener to update 'updated' column before each update
@event.listens_for(UserRole, "before_update")
def before_update_user_role_listener(mapper, connection, target):
    target.updated = datetime.utcnow()


class UserTag(db.Model):
    __tablename__ = "user_tags"
    __table_args__ = (UniqueConstraint("user_id", "tag", name="user_id_tag"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship("User", back_populates="tags")
    tag = db.Column(db.String(512), nullable=False, index=True)
    value = db.Column(db.Text, nullable=False, default='', index=True)
    flair = db.Column(db.String(2048), nullable=False, default='')
    # If set, will replace the flair with the custom emoji URL from the instance
    custom_emoji = db.Column(db.String(2048), nullable=True, index=True)
    # A description of this tag. To be used by UIs on mouseovers etc.
    description = db.Column(db.Text, nullable=True)
    expires = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class UserFlag(db.Model):
    __tablename__ = "user_flags"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship("User", back_populates="flags")
    flag = db.Column(db.String(512), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False, default='')
    expires = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Define event listener to update 'updated' column before each update
@event.listens_for(UserTag, "before_update")
def before_update_user_tag_listener(mapper, connection, target):
    target.updated = datetime.utcnow()

class UserInvite(db.Model):
    __tablename__ = "user_invites"
    id = db.Column(uuid_column_type(), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship("User", back_populates="invites")
    comment = db.Column(db.Text, nullable=True)
    expires = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    invited_users = db.relationship("User", back_populates="invited")

# Define event listener to update 'updated' column before each update
@event.listens_for(UserInvite, "before_update")
def before_update_user_tag_listener(mapper, connection, target):
    target.updated = datetime.utcnow()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_url = db.Column(db.String(1023), unique=True, nullable=False, index=True)
    api_key = db.Column(db.String(100), unique=True, nullable=True, index=True)
    # Used when their donation email is different from their user email
    email_override = db.Column(db.String(1024), unique=True, nullable=True, index=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    invited_id = db.Column(
        uuid_column_type(),
        db.ForeignKey("user_invites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    invited = db.relationship("UserInvite", back_populates="invited_users")

    roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    tags = db.relationship("UserTag", back_populates="user", cascade="all, delete-orphan")
    flags = db.relationship("UserFlag", back_populates="user", cascade="all, delete-orphan")
    invites = db.relationship("UserInvite", back_populates="user", cascade="all, delete-orphan")
    filters = db.relationship("Filter", back_populates="user")
    filter_appeals_resolved = db.relationship("FilterAppeal", back_populates="resolver")
    governance_posts = db.relationship("GovernancePost", back_populates="user", cascade="all, delete-orphan")
    governance_post_comments = db.relationship("GovernancePostComment", back_populates="user", cascade="all, delete-orphan")

    def add_role(self, role: UserRoleTypes) -> None:
        if not isinstance(role, UserRoleTypes):
            raise e.DBException(f"{role} not a valid role")
        existing_role = UserRole.query.filter_by(
            user_id=self.id,
            user_role=role,
            value=True,
        ).first()
        if existing_role:
            return
        new_role = UserRole(
            user_id=self.id,
            user_role=role,
            value=True,
        )
        db.session.add(new_role)
        db.session.commit()

    def remove_role(self, role: UserRoleTypes) -> None:
        if not isinstance(role, UserRoleTypes):
            raise e.DBException(f"{role} not a valid role")
        existing_role = UserRole.query.filter_by(
            user_id=self.id,
            user_role=role,
            value=True,
        ).first()
        if not existing_role:
            return
        db.session.delete(existing_role)
        db.session.commit()

    def has_role(self, role: UserRoleTypes) -> bool:
        return (
            UserRole.query.filter_by(
                user_id=self.id,
                user_role=role,
                value=True,
            ).count()
            == 1
        )

    def set_tag(
            self, 
            tag: str, 
            value: str, 
            flair: str | None = None, 
            custom_emoji: str | None = None, 
            expires: datetime | None = None) -> None:
        assert isinstance(tag, str)
        tag = tag.lower()
        existing_tag = UserTag.query.filter_by(
            user_id=self.id,
            tag=tag,
        ).first()
        if tag in ["ko-fi_tier", "liberapay_tier"]:
            if value in Config.trusted_tiers:
                self.add_role(UserRoleTypes.TRUSTED)
            if value in Config.known_tiers:
                self.add_role(UserRoleTypes.KNOWN)
            if value in Config.voting_tiers:
                self.add_role(UserRoleTypes.VOTING)
        if tag in Config.trusted_tags and value != "false":
            self.add_role(UserRoleTypes.TRUSTED)
        if tag in Config.known_tags and value != "false":
            self.add_role(UserRoleTypes.KNOWN)
        if tag in Config.voting_tags and value != "false":
            self.add_role(UserRoleTypes.VOTING)
        if existing_tag:
            existing_tag.value = value
            existing_tag.flair = flair
            existing_tag.expires = expires
            existing_tag.custom_emoji = custom_emoji
            db.session.commit()
            return
        new_tag = UserTag(
            user_id=self.id,
            tag=tag,
            value=value,
            flair=flair,
            expires=expires,
            custom_emoji=custom_emoji,
        )
        db.session.add(new_tag)
        db.session.commit()

    def remove_tag(self, tag: str) -> None:
        assert isinstance(tag, str)
        tag = tag.lower()
        existing_tag = UserTag.query.filter_by(
            user_id=self.id,
            tag=tag,
        ).first()
        if not existing_tag:
            return
        db.session.delete(existing_tag)
        db.session.commit()

    def get_tag(self, tag: str) -> str | None:
        assert isinstance(tag, str)
        tag = tag.lower()
        return (
            UserTag.query.filter_by(
                user_id=self.id,
                tag=tag,
            ).first()
        )

    def set_flag(
            self, 
            flag: str, 
            reason: str,
            expires: datetime | None = None) -> None:
        assert isinstance(flag, str)
        flag = flag.lower()
        new_flag = UserFlag(
            user_id=self.id,
            flag=flag,
            reason=reason,
            expires=expires,
        )
        db.session.add(new_flag)
        db.session.commit()

    def is_moderator(self) -> bool:
        return self.has_role(UserRoleTypes.ADMIN) or self.has_role(UserRoleTypes.MODERATOR)

    def is_muted(self) -> bool:
        return self.has_role(UserRoleTypes.MUTED)

    def can_do_filters(self) -> bool:
        return self.is_moderator()

    def can_do_user_operations(self) -> bool:
        return self.is_moderator()

    def can_create_mods(self) -> bool:
        return self.has_role(UserRoleTypes.ADMIN)

    def has_tag(self, tag: str) -> bool:
        return (
            UserTag.query.filter_by(
                user_id=self.id,
                tag="vouched",
            ).count()
            == 1
        )

    def is_known(self) -> bool:
        for role in self.roles:
            # Doing it this way instead of using has_role to avoid 4 distinct calls to the DB
            if role.user_role in [
                UserRoleTypes.KNOWN, 
                UserRoleTypes.TRUSTED, 
                UserRoleTypes.MODERATOR, 
                UserRoleTypes.ADMIN
            ]:
                return True
        return self.has_tag("vouched")

    def can_vote(self) -> bool:
        for role in self.roles:
            # Doing it this way instead of using has_role to avoid 4 distinct calls to the DB
            # FIXME: Can probably do it with a single db count to save pulling all the roles.
            if role.user_role in [
                UserRoleTypes.VOTING, 
                UserRoleTypes.TRUSTED, 
                UserRoleTypes.MODERATOR, 
                UserRoleTypes.ADMIN
            ]:
                return True
        return self.has_tag("vouched")

    def is_trusted(self) -> bool:
        for role in self.roles:
            # Doing it this way instead of using has_role to avoid 3 distinct calls to the DB
            if role.user_role in [
                UserRoleTypes.TRUSTED, 
                UserRoleTypes.MODERATOR, 
                UserRoleTypes.ADMIN
            ]:
                return True
        return False

    def can_create_trust(self) -> bool:
        return self.is_moderator()

    def count_flags(self,flag: str) -> int:
        return db.session.query(UserFlag).filter_by(user_id=self.id).filter_by(flag=flag).count()


    def compile_tags_list(self):
        tags = []
        for t in self.tags:
            # If the tag has a custom emoji attached, use that as the flair
            flair = lemmy_emoji.get_emoji_url(t.custom_emoji) if t.custom_emoji else t.flair
            # If the tag is a known custom emoji flair, use that as the flair
            if t.tag in Config.predefined_custom_emoji_flairs:
                flair = lemmy_emoji.get_emoji_url(Config.predefined_custom_emoji_flairs[t.tag])
            if t.description:
                description = t.description
            elif t.tag in ["ko-fi_tier", "liberapay_tier", "patreon_tier"]:
                description = Config.payment_tier_descriptions[t.value]
            elif t.tag in Config.predefined_tag_descriptions:
                description = Config.predefined_tag_descriptions[t.tag]
            tags.append({
                "tag": t.tag, 
                "value": t.value,
                "flair": flair,
                "expires": t.expires,
                "description": description,
            })
        red_flag_count = self.count_flags("warning")
        if red_flag_count > 0:
            flair = "red_flag"
            if red_flag_count > 1:
                flair = "double_red_flag"
            tags.append({
                "tag": "warning_flags",
                "value": True,
                "flair": lemmy_emoji.get_emoji_url(flair),
                "expires": None,
                "description": Config.flag_descriptions[flair],
            })
        return tags

    def get_details(self, privilege=0) -> dict:
        user_details = {
            "id": self.id,
            "user_url": self.user_url,
            "roles": [role.user_role for role in self.roles],
            "tags": self.compile_tags_list(),
            "created": self.created,
            "updated": self.updated,
        }
        if privilege > 0:
            user_details["override"] = self.email_override
            user_details["invited_by"] = self.invited.user.user_url if self.invited else None
        return user_details

    def get_all_flairs(self):
        return [tag["flair"] for tag in self.compile_tags_list() if tag["flair"]]
            
    def get_all_flair_markdowns(self):
        flair_markdowns = []
        for t in self.tags:
            if t.custom_emoji:
                flair_markdowns.append(lemmy_emoji.get_emoji_markdown(t.custom_emoji))
                continue
            if t.tag in Config.predefined_custom_emoji_flairs:
                flair_markdowns.append(lemmy_emoji.get_emoji_markdown(Config.predefined_custom_emoji_flairs[t.tag]))
        return flair_markdowns
    
    @logger.catch(reraise=True)
    def get_most_significant_flair_shortcode(self, flair_priorities = Config.voting_flair_priority) -> str | None:
        order_of_flair = flair_priorities
        lowest_flair = None
        lowest_tag = None
        for t in self.tags:
            shortcode = None
            if t.value in order_of_flair:
                flair_prio = order_of_flair[t.value]
                shortcode = t.value
            elif t.tag in order_of_flair:
                flair_prio = order_of_flair[t.tag]
                shortcode = t.tag
            else:
                continue
            if not lowest_flair:
                lowest_flair = shortcode
                lowest_tag = t
                continue
            if flair_prio < order_of_flair[lowest_flair]:
                lowest_flair = shortcode
                lowest_tag = t                
        if lowest_tag and lowest_tag.custom_emoji:
            lowest_flair = lowest_tag.custom_emoji
        if lowest_flair in Config.predefined_custom_emoji_flairs:
            lowest_flair = Config.predefined_custom_emoji_flairs[lowest_flair]
        return lowest_flair

    
    def get_most_significant_voting_flair_markdown(self) -> str:
        shortcode = self.get_most_significant_flair_shortcode(Config.voting_flair_priority)
        return lemmy_emoji.get_emoji_markdown(shortcode)


    def get_most_significant_non_voting_flair_markdown(self) -> str:
        shortcode = self.get_most_significant_flair_shortcode(Config.non_voting_flair_priority)
        return lemmy_emoji.get_emoji_markdown(shortcode)


@event.listens_for(User, "before_update")
def before_update_user_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
