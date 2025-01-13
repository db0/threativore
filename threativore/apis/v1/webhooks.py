from flask_restx import Resource, reqparse
from threativore.flask import cache, db
from loguru import logger
from threativore import database
from threativore import exceptions as e
from threativore.main import threativore
from threativore.config import Config
from threativore.enums import UserRoleTypes
from threativore import utils
from threativore.apis.v1.base import *
from threativore.lemmy_db import get_actor_id_from_email

class KoFi(Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument("verification_token", type=str, required=True, location="json")
    post_parser.add_argument("message_id", type=str, required=True, location="json")
    post_parser.add_argument("timestamp", type=str, required=True, location="json")
    post_parser.add_argument("type", type=str, required=True, location="json")
    post_parser.add_argument("is_public", type=bool, required=True, location="json")
    post_parser.add_argument("from_name", type=str, required=True, location="json")
    post_parser.add_argument("message", type=str, location="json")
    post_parser.add_argument("amount", type=str, required=True, location="json")
    post_parser.add_argument("url", type=str, location="json")
    post_parser.add_argument("email", type=str, location="json")
    post_parser.add_argument("currency", type=str, required=True, location="json")
    post_parser.add_argument("is_subscription_payment", type=bool, location="json")
    post_parser.add_argument("is_first_subscription_payment", type=bool, location="json")
    post_parser.add_argument("kofi_transaction_id", type=str, location="json")
    post_parser.add_argument("shop_items", type=dict, location="json")
    post_parser.add_argument("tier_name", type=str, location="json")
    post_parser.add_argument("shipping", type=dict, location="json")

    @api.expect(post_parser, models.response_model_kofi_webhook, validate=True)
    @api.marshal_with(models.response_model_simple_response, code=200, description='Ingest Ko-Fi webhook', skip_none=True)
    def post(self):
        '''Ko-Fi webhook input
        '''
        self.args = self.post_parser.parse_args()
        if self.args.verification_token != Config.kofi_webhook_verification_token:
            raise e.BadRequest("Invalid verification token")
        user = database.get_user_from_override_email(self.args.email)
        if not user:
            actor_id = get_actor_id_from_email(self.args.email)
            if not actor_id:
                raise e.BadRequest(f"Ko-Fi donation from {self.args.email} but no user from that email found in our instance.")
                # logger.warning(f"Ko-Fi donation from {self.args.email} but no user from that email found in our instance.")
                # return {"message": "OK"}, 200
        user = threativore.users.ensure_user_exists(actor_id)
        tier = "drinking mate"
        if self.args.is_subscription_payment and self.args.tier_name:
            tier = self.args.tier_name
        user.set_tag("ko-fi_tier", tier)
        user.set_tag("ko-fi_donation_time", self.args.timestamp)
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
