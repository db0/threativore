from datetime import datetime

from sqlalchemy import Enum, event

from threagetarian.enums import FilterAction, FilterType
from threagetarian.flask import db


class FilterMatch(db.Model):
    """For storing triggered filters and the user"""

    __tablename__ = "filter_matches"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    entity_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    url = db.Column(db.Text, nullable=False)
    actor_id = db.Column(db.Text, nullable=False, index=True)
    filter_id = db.Column(db.Integer, db.ForeignKey("filters.id", ondelete="CASCADE"))
    filter = db.relationship("Filter", back_populates="filter_matches")
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


# Define event listener to update 'updated' column before each update
@event.listens_for(FilterMatch, "before_update")
def before_update_filter_match_listener(mapper, connection, target):
    target.updated = datetime.utcnow()


class Filter(db.Model):
    """For storing detection regex"""

    __tablename__ = "filters"
    id = db.Column(db.Integer, primary_key=True)
    regex = db.Column(db.Text, index=True)
    description = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    filter_action = db.Column(Enum(FilterAction), nullable=False)
    filter_type = db.Column(Enum(FilterType), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="filters")
    filter_matches = db.relationship("FilterMatch", back_populates="filter")
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
