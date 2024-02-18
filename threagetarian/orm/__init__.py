from threagetarian.flask import APP, db
from threagetarian.orm.filters import Filter
from threagetarian.orm.seen import Seen
from threagetarian.orm.user import User

with APP.app_context():
    db.create_all()


__all__ = [
    "User",
    "Filter",
    "Seen",
]
