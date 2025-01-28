from datetime import datetime

from sqlalchemy import Enum, UniqueConstraint, event

from threativore.enums import FilterAction, FilterType, EntityType, AppealStatus
from threativore.orm.user import User
from threativore.flask import db

class FilterAppeal(db.Model):
    """For storing sent appeals"""
    __tablename__ = "filter_appeals"
    __table_args__ = (UniqueConstraint("creator_url", "filter_match_id", name="creator_url_filter_match_id_unique"),)
    __allow_unmapped__ = True
    
    id: int = db.Column(db.Integer, primary_key=True)
    # The ID of the PM which triggered this appeal
    pm_id: int = db.Column(db.Integer, unique=True, nullable=False)
    # The ID url of the person who PM'd threativore. We use this to PM them back with any replies.
    creator_id: int = db.Column(db.Integer, nullable=False, index=True)
    creator_url: str = db.Column(db.String(1023), nullable=False, index=True)
    # The message sent with the appeal
    message: str = db.Column(db.Text, nullable=True)
    # The reply (if any) sent from the results of the appeal.
    reply: str = db.Column(db.Text, nullable=True)
    # Whether anyone saw/actioned this appeal
    status: AppealStatus = db.Column(Enum(AppealStatus), nullable=False, index=True, default=AppealStatus.PENDING)
    filter_match_id: int = db.Column(db.Integer, db.ForeignKey("filter_matches.id", ondelete="CASCADE"), index=True, nullable=False)
    filter_match: "FilterMatch" = db.relationship("FilterMatch", back_populates="appeals")
    filter_id: int = db.Column(db.Integer, db.ForeignKey("filters.id", ondelete="CASCADE"), index=True, nullable=False)
    filter: "Filter" = db.relationship("Filter", back_populates="appeals")
    resolver_id: int = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolver: User = db.relationship("User", back_populates="filter_appeals_resolved")
    created: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# Define event listener to update 'updated' column before each update
@event.listens_for(FilterAppeal, "before_update")
def before_update_appeal_filter_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
    
class FilterMatch(db.Model):
    """For storing triggered filters and the user"""

    __tablename__ = "filter_matches"
    __allow_unmapped__ = True    

    id: int = db.Column(db.Integer, primary_key=True)
    report_id: int = db.Column(db.Integer, unique=True, nullable=True, index=True)
    entity_id: int = db.Column(db.Integer, unique=True, nullable=False, index=True)
    # For filter matches this will only ever be COMMENT or POST.
    entity_type: EntityType = db.Column(Enum(EntityType), nullable=False, index=True)
    url: str = db.Column(db.Text, nullable=False)
    content: str = db.Column(db.Text, nullable=False)
    actor_id: str = db.Column(db.Text, nullable=False, index=True)
    filter_id: int = db.Column(db.Integer, db.ForeignKey("filters.id", ondelete="CASCADE"))
    filter: "Filter" = db.relationship("Filter", back_populates="filter_matches")
    appeals: list[FilterAppeal] = db.relationship("FilterAppeal", back_populates="filter_match")
    created: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# Define event listener to update 'updated' column before each update
@event.listens_for(FilterMatch, "before_update")
def before_update_filter_match_listener(mapper, connection, target):
    target.updated = datetime.utcnow()


class Filter(db.Model):
    """For storing detection regex"""

    __tablename__ = "filters"
    __allow_unmapped__ = True    
    
    id: int = db.Column(db.Integer, primary_key=True)
    regex: str = db.Column(db.Text, index=True)
    description: str = db.Column(db.Text, nullable=True)
    scope: str = db.Column(db.Text, nullable=False, default='global', index=True)
    reason: str = db.Column(db.Text, nullable=False)
    filter_action: FilterAction = db.Column(Enum(FilterAction), nullable=False)
    filter_type: FilterType = db.Column(Enum(FilterType), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    user: User = db.relationship("User", back_populates="filters")
    filter_matches: list[FilterMatch] = db.relationship("FilterMatch", back_populates="filter")
    appeals: list[FilterAppeal] = db.relationship("FilterAppeal", back_populates="filter")
    created: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def get_details(self):
        return {
            "id": self.id,
            "regex": self.regex,
            "description": self.description,
            "user": self.user.user_url,
        }


# Define event listener to update 'updated' column before each update
@event.listens_for(Filter, "before_update")
def before_update_filter_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
