from flask_restx import Resource, reqparse
from flask import request
from threativore.flask import cache
from loguru import logger
from threativore import database
from threativore import exceptions as e
from threativore.apis.v1.base import *
from threativore.config import Config
from threativore.main import threativore
from threativore import utils


class Tag(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument("apikey", type=str, required=True, help="A threativore admin key.", location='headers')
    get_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")

    @api.expect(get_parser)
    # @cache.cached(timeout=600)
    # @api.marshal_with(models.response_model_open_votes, code=200, description='Get Open Voting Threads', as_list=True)
    def get(self, tag):
        '''List all users which have a specific tag
        '''
        self.args = self.get_parser.parse_args()        
        if self.args.apikey not in Config.admin_api_keys:
            raise e.Unauthorized("Invalid API key")        
        return [
            {
                "user": t.user.user_url,
                "value": t.value
            } for t in database.get_all_tags(tag)],200

    post_parser = reqparse.RequestParser()
    post_parser.add_argument("apikey", type=str, required=True, help="A threativore admin key.", location='headers')
    post_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")
    post_parser.add_argument("target_user_url", type=str, required=True, help="The user to which to assign this tag", location="json")
    post_parser.add_argument("value", type=str, default="true", help="The value to assign to this tag", location="json")

    @api.expect(post_parser)
    # @api.marshal_with(models.response_model_open_votes, code=200, description='Get Open Voting Threads', as_list=True)
    def post(self, tag):
        '''Add a tag to a specific user
        '''
        self.args = self.post_parser.parse_args()        
        if self.args.apikey not in Config.admin_api_keys:
            raise e.Unauthorized("Invalid API key")
        flair_tag = utils.get_predefined_tag_from_flair(tag)
        if "https" not in self.args.target_user_url:
            raise e.BadRequest(f"{self.args.target_user_url} is not a user URL")
        value = self.args.value
        # If they don't provide a user URL value, we set the admin username as the value for vouches
        # So we can still track the chain
        if tag == "vouched" and "https" not in self.args.value:
            value = Config.admin_api_keys[self.args.apikey]
        threativore_user = database.get_user(self.args.target_user_url)
        if threativore_user:
            existing_flair = database.get_tag(flair_tag, threativore_user.id)
            if existing_flair: 
                return {
                    "message": "ok",
                    "user_added": False
                }
        user_added = False
        if not threativore_user:
            user_added = True
            threativore_user = self.threativore.users.ensure_user_exists(utils.username_to_url(target_user))
        threativore_user.set_tag(
            tag=flair_tag, 
            value=value,
        )
        return {
            "message": "changed",
            "user_added": user_added
        }

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("apikey", type=str, required=True, help="A threativore admin key.", location='headers')
    delete_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")
    delete_parser.add_argument("target_user_url", type=str, required=True, help="The user from which to delete this tag", location="json")

    @api.expect(delete_parser)
    # @api.marshal_with(models.response_model_open_votes, code=200, description='Get Open Voting Threads', as_list=True)
    def delete(self, tag):
        '''Delete a tag from a specific user
        '''
        self.args = self.delete_parser.parse_args()        
        if self.args.apikey not in Config.admin_api_keys:
            raise e.Unauthorized("Invalid API key")        
        flair_tag = utils.get_predefined_tag_from_flair(tag)
        #TODO: More rigorous
        if "https" not in self.args.target_user_url:
            raise e.BadRequest(f"{self.args.target_user_url} is not a user URL")
        threativore_user = database.get_user(self.args.target_user_url)
        if threativore_user:
            existing_flair = database.get_tag(flair_tag, threativore_user.id)
            if not existing_flair: 
                return {
                    "message": "ok",
                    "user_added": False
                }
        if not threativore_user:
            return {
                "message": "ok",
                "user_added": False
            }
        threativore_user.remove_tag(flair_tag)
        return {
            "message": "changed",
            "user_added": False
        }
