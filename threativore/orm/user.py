from datetime import datetime, timedelta

from sqlalchemy import Enum, UniqueConstraint, event

import threativore.exceptions as e
from threativore.enums import UserRoleTypes
from threativore.flask import db
from loguru import logger


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
    flair = db.Column(db.String(2048), nullable=False, default='', index=True)
    expires = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# Define event listener to update 'updated' column before each update
@event.listens_for(UserTag, "before_update")
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

    roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    tags = db.relationship("UserTag", back_populates="user", cascade="all, delete-orphan")
    filters = db.relationship("Filter", back_populates="user")
    filter_appeals_resolved = db.relationship("FilterAppeal", back_populates="resolver")

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
            expires: datetime | None = None) -> None:
        assert isinstance(tag, str)
        tag = tag.lower()
        existing_tag = UserTag.query.filter_by(
            user_id=self.id,
            tag=tag,
        ).first()
        if existing_tag:
            existing_tag.value = value
            existing_tag.flair = flair
            existing_tag.expires = expires
            db.session.commit()
            return
        new_tag = UserTag(
            user_id=self.id,
            tag=tag,
            value=value,
            flair=flair,
            expires=expires,
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

    def is_known(self) -> bool:
        return self.has_role(UserRoleTypes.ADMIN) or self.has_role(UserRoleTypes.MODERATOR) or self.has_role(UserRoleTypes.TRUSTED)

    def can_create_trust(self) -> bool:
        return self.is_moderator()
    
    def get_details(self, privilege=0) -> dict:
        for tag in self.tags:
            if tag == "ko-fi_tier":
                expiration_time = UserTag.query.filter_by(
                    user_id=self.id,
                    tag="ko-fi_donation_time",
                    ).first()
                if expiration_time.value < datetime.utcnow() - timedelta(days=60):
                    self.remove_tag("ko-fi_tier")
        user_details = {
            "id": self.id,
            "user_url": self.user_url,
            "roles": [role.user_role for role in self.roles],
            "tags": [
                {
                    "tag": t.tag, 
                    "value": t.value,
                    "flair": t.flair,
                    "expires": t.expires,
                } for t in self.tags
            ],
            "created": self.created,
            "updated": self.updated,
        }
        if privilege > 0:
            user_details["override"] = self.email_override
        return user_details


@event.listens_for(User, "before_update")
def before_update_user_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
