import threativore.apis.v1.user as user
import threativore.apis.v1.governance as governance
import threativore.apis.v1.webhooks as webhooks
from threativore.apis.v1.user import api

api.add_resource(user.User, "/user/<string:username>")
api.add_resource(governance.OpenVotes, "/open_votes")
api.add_resource(webhooks.KoFi, "/webhooks/kofi")
