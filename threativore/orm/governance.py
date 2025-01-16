
from datetime import datetime, timedelta

from sqlalchemy import Enum, UniqueConstraint, event

import threativore.exceptions as e
from threativore.flask import db
from threativore.emoji import lemmy_emoji
from threativore.config import Config
from loguru import logger
from threativore.enums import GovernancePostType


class GovernancePostComment(db.Model):
    __tablename__ = "governance_post_comments"
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, nullable=False, index=True)
    comment_id = db.Column(db.Integer, nullable=False, index=True)
    replied = db.Column(db.Boolean, default=True, nullable=False, index=True)
    gpost_id = db.Column(
        db.Integer,
        db.ForeignKey("governance_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gpost = db.relationship("GovernancePost", back_populates="post_comments")
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = db.relationship("User", back_populates="gpost_comments")
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Define event listener to update 'updated' column before each update
@event.listens_for(GovernancePostComment, "before_update")
def before_update_user_tag_listener(mapper, connection, target):
    target.updated = datetime.utcnow()

class GovernancePost(db.Model):
    __tablename__ = "governance_posts"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    post_url = db.Column(db.String(2048), unique=True, nullable=False, index=True)
    control_comment_id = db.Column(db.Integer, unique=True, nullable=True)
    post_type = db.Column(Enum(GovernancePostType), nullable=False, default=GovernancePostType.SIMPLE_MAJORITY)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upvotes = db.Column(db.Integer, nullable=False, default=0)
    downvotes = db.Column(db.Integer, nullable=False, default=0)
    user = db.relationship("User", back_populates="governance_posts")
    newest_comment_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires = db.Column(db.DateTime, default=datetime.utcnow + timedelta(days=7), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    post_comments = db.relationship("GovernancePostComments", back_populates="user", cascade="all, delete-orphan")


# Define event listener to update 'updated' column before each update
@event.listens_for(GovernancePost, "before_update")
def before_update_user_tag_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
