from threativore.flask import APP, db
from threativore.orm.filters import Filter
from threativore.orm.governance import GovernancePost
from threativore.orm.seen import Seen
from threativore.orm.user import User

with APP.app_context():
    db.create_all()


__all__ = [
    "User",
    "Filter",
    "Seen",
    "GovernancePost",
]
