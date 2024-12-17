from datetime import datetime

from sqlalchemy import Enum, UniqueConstraint, event

import threativore.exceptions as e
from threativore.enums import UserRoleTypes
from threativore.flask import db


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


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_url = db.Column(db.String(1023), unique=True, nullable=False, index=True)
    api_key = db.Column(db.String(100), unique=True, nullable=True, index=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    filters = db.relationship("Filter", back_populates="user")
    filter_appeals_resolved = db.relationship("FilterAppeals", back_populates="resolver")

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

    def is_moderator(self) -> bool:
        return self.has_role(UserRoleTypes.ADMIN) or self.has_role(UserRoleTypes.MODERATOR)

    def is_muted(self) -> bool:
        return self.has_role(UserRoleTypes.MUTED)

    def can_do_filters(self) -> bool:
        return self.is_moderator()

    def can_create_mods(self) -> bool:
        return self.has_role(UserRoleTypes.ADMIN)

    def can_create_trust(self) -> bool:
        return self.is_moderator()


@event.listens_for(User, "before_update")
def before_update_user_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
