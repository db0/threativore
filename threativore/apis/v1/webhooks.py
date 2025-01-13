import json
from flask import request
from flask_restx import Resource, reqparse
from threativore import exceptions as e
from threativore.flask import cache, db
from loguru import logger
from threativore import database
from threativore.main import threativore
from threativore.config import Config
from threativore.enums import UserRoleTypes
from threativore import utils
from threativore.apis.v1.base import *
from threativore.lemmy_db import get_actor_id_from_email

class KoFi(Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument("data", type=str, required=True, location="form")

    @api.expect(post_parser)
    @api.marshal_with(models.response_model_simple_response, code=200, description='Ingest Ko-Fi webhook', skip_none=True)
    def post(self):
        '''Ko-Fi webhook input
        '''
        logger.debug(f"Ko-Fi donation Request: {request.form}")
        self.args = self.post_parser.parse_args()
        try:
            data = json.loads(self.args.data)
        except json.JSONDecodeError:
            raise e.BadRequest("Invalid JSON in data field")

        if data.get("verification_token") != Config.kofi_webhook_verification_token:
            raise e.BadRequest("Invalid verification token")

        user = database.get_user_from_override_email(data.get("email"))
        if not user:
            actor_id = get_actor_id_from_email(data.get("email"))
            if not actor_id:
                raise e.BadRequest(f"Ko-Fi donation from {data.get('email')} but no user from that email found in our instance.")
        user = threativore.users.ensure_user_exists(actor_id)
        tier = "drinking mate"
        if data.get("is_subscription_payment") and data.get("tier_name"):
            tier = data.get("tier_name")
        user.set_tag("ko-fi_tier", tier)
        user.set_tag("ko-fi_donation_time", data.get("timestamp"))
        threativore.reply_to_user_url(
            actor_id, 
            (
                'Arr matey! Your donation to the ![a pirate chest full of doubloons](https://lemmy.dbzer0.com/pictrs/image/af140ff3-a09d-4b9c-8907-15d34d674c0e.png "booty") is acknowledged and will go towards '
                "the upkeep of the ship. "
                f"You have been marked as a {tier} for {Config.donation_expiration_days} more days. "
                'Thank ye! ![pirate captain giving the thumbs up](https://lemmy.dbzer0.com/pictrs/image/bc10b52a-196d-4e4a-98a2-bfd2dbb10d9a.png "thumbsup")'
            )
                
        )
        return {"message": "OK"}, 200
