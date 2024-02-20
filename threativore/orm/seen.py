from datetime import datetime

from sqlalchemy import Enum, UniqueConstraint, event

from threativore.enums import EntityType
from threativore.flask import db


class Seen(db.Model):
    __tablename__ = "seen"
    __table_args__ = (UniqueConstraint("entity_id", "entity_type", name="entity_id_type"),)

    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, unique=False, nullable=False, index=True)
    entity_type = db.Column(Enum(EntityType), nullable=False, index=True)
    entity_url = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


@event.listens_for(Seen, "before_update")
def before_update_seen_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
