from flask_restx import fields
from threativore import enums

class Models:
    def __init__(self,api):
        self.response_model_error = api.model('RequestError', {
            'message': fields.String(description="The error message for this status code."),
        })
        self.response_model_simple_response = api.model('SimpleResponse', {
            "message": fields.String(default='OK',required=True, description="The result of this operation."),
        })
        self.response_model_UserTags = api.model('UserTags', {
            'tag': fields.String(description="A user's tag"),
            'value': fields.String(description="A user's tag value"),
            'flair': fields.String(description="A user's tag flair value", required=False),
            'expires': fields.String(description="A user's tag expiry date", required=False),
            'description': fields.String(description="A description for the tag", required=False),
        })
        self.response_model_model_User_get = api.model('User', {
            'user_url': fields.String(description="The user's URL"),
            'roles': fields.List(fields.String(description="The user's roles", enum=[i.name for i in enums.UserRoleTypes])),
            'tags': fields.List(fields.Nested(self.response_model_UserTags)),
            'aliases': fields.List(fields.String(required=True,description="An alias of the same user in a different instance")),
            'override': fields.String(required=False,description="an override for the user account coming from a payment provider. Can be either an email or username."),
        })
        self.response_model_model_User_put = api.model('User', {
            'roles': fields.List(fields.String(description="The user's roles", enum=[i.name for i in enums.UserRoleTypes])),
            'tags': fields.List(fields.Nested(self.response_model_UserTags)),
            'override': fields.String(required=False,description="an override for the user account coming from a payment provider. Can be either an email or username."),
        })
        self.response_model_model_User_patch = api.model('User', {
            'roles': fields.List(fields.String(description="The user's roles", enum=[i.name for i in enums.UserRoleTypes])),
            'tags': fields.List(fields.Nested(self.response_model_UserTags)),
            'override': fields.String(required=False, description="an override for the user account coming from a payment provider. Can be either an email or username."),
            'delete_unspecified_values': fields.Boolean(default=False, required=False,description="Delete unspecified values"),
        })

        # FIXME: Doesn't work. Crashes API
        self.input_model_kofi_webhook = api.model('Ko-fi Webhook', {
            'verification_token': fields.String(required=True, description="Verification token"),
            'message_id': fields.String(required=True, description="Message ID"),
            'timestamp': fields.DateTime(required=True, description="Timestamp"),
            'type': fields.String(required=True, description="Type of the donation"),
            'is_public': fields.Boolean(required=True, description="Is the donation public"),
            'from_name': fields.String(required=True, description="Name of the donor"),
            'message': fields.String(description="Message from the donor"),
            'amount': fields.String(required=True, description="Amount donated"),
            'url': fields.String(description="URL of the donation"),
            'email': fields.String(description="Email of the donor"),
            'currency': fields.String(required=True, description="Currency of the donation"),
            'is_subscription_payment': fields.Boolean(description="Is it a subscription payment"),
            'is_first_subscription_payment': fields.Boolean(description="Is it the first subscription payment"),
            'kofi_transaction_id': fields.String(description="Ko-fi transaction ID"),
            'shop_items': fields.Raw(description="Shop items"),
            'tier_name': fields.String(description="Tier name"),
            'shipping': fields.Raw(description="Shipping information"),
        })
        self.input_model_kofi_webhook_data = api.model('Ko-fi Webhook Data', {
            'data': fields.Nested(self.input_model_kofi_webhook),
        })
        self.response_model_open_votes = api.model('OpenVotes', {
            'post_url': fields.String(description="URL of the post", example="lemmy.dbzer0.com/post/36114134"),
            'control_comment_url': fields.String(description="URL of the control comment", example="lemmy.dbzer0.com/comment/16153945"),
            'post_type': fields.String(description="Type of the post", example="SIMPLE_MAJORITY", enum=[i.name for i in enums.GovernancePostType]),
            'user_url': fields.String(description="URL of the user", example="https://lemmy.dbzer0.com/u/flatworm7591"),
            'newest_comment_time': fields.DateTime(description="Time of the newest comment"),
            'expires': fields.DateTime(description="Expiration time"),
            'created': fields.DateTime(description="Creation time"),
        })
