# Quick and dirty keystore implementation
# to store key-value pairs in the database
from datetime import datetime

from sqlalchemy import event

from threativore.flask import db
from threativore.config import Config
from sqlalchemy.dialects.postgresql import JSONB, JSON
import json
json_column_type = JSONB if not Config.use_sqlite else JSON

class KeyStore(db.Model):
    __tablename__ = "keystore"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=True, index=True)
    value = db.Column(json_column_type, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires = db.Column(db.DateTime, nullable=True, index=True)

    @classmethod
    def get_keyvalue(cls, key):
        record = cls.query.filter_by(key = key).first()
        # TODO: Set DB to delete expired records automatically when using PostgreSQL
        if record and record.expires and record.expires < datetime.utcnow():
            db.session.delete(record)
            db.session.commit()
            return None
        return record.value if record and record.value else None

    @classmethod
    def set_keyvalue(cls, key, value, expires=None):        
        record = cls.query.filter_by(key=key).first()
        if record:
            record.value = value
            record.expires = expires
        else:
            record = cls(key=key, value=value, expires=expires)
            db.session.add(record)
        db.session.commit()

    @classmethod
    def delete_key(cls, key):
        record = cls.query.filter_by(key=key).first()
        if record:
            db.session.delete(record)
            db.session.commit()

    @classmethod
    def get_previous_blocklist(cls):
        value =  cls.get_keyvalue("previous_blocklist")
        if value:
            return set(value)
        else:
            return None

    @classmethod
    def get_validating_blocklist(cls):
        value =  cls.get_keyvalue("validating_blocklist")
        if value:
            return set(value)
        else:
            return None


@event.listens_for(KeyStore, "before_update")
def before_update_seen_listener(mapper, connection, target):
    target.updated = datetime.utcnow()
