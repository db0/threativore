import threativore.apis.v1.user as user
import threativore.apis.v1.webhooks as webhooks
from threativore.apis.v1.user import api

api.add_resource(user.User, "/user/<string:username>")
api.add_resource(webhooks.KoFi, "/webhooks/kofi")
