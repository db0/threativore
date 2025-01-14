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

class User(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")

    @api.expect(get_parser)
    @cache.cached(timeout=10)
    @api.marshal_with(models.response_model_model_User_get, code=200, description='Get User details', skip_none=True)
    def get(self,username):
        '''Details about a specific user
        '''
        user_url = utils.username_to_url(username)
        user = database.get_user(user_url)
        if not user:
            raise e.NotFound(f"{user_url} not found")
        return user.get_details(),200
        
    put_parser = reqparse.RequestParser()
    put_parser.add_argument("apikey", type=str, required=True, help="A threativore admin key.", location='headers')
    put_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")
    put_parser.add_argument(
            "tags",
            type=list,
            required=False,
            help="User tags to assign to this user.",
            location="json",
        )
    put_parser.add_argument(
            "roles",
            type=list,
            required=False,
            help="List of roles to set for this user.",
            location="json",
        )
    
    @api.expect(put_parser, models.response_model_model_User_put, validate=True)
    @api.marshal_with(models.response_model_model_User_get, code=200, description='Add new user', skip_none=True)
    @api.response(400, 'Bad Request', models.response_model_error)
    @api.response(401, 'Invalid API Key', models.response_model_error)
    @api.response(403, 'Access Denied', models.response_model_error)
    def put(self,username):
        '''Adds a new user to threativore
        '''
        self.args = self.put_parser.parse_args()
        user_url = utils.username_to_url(username)
        if self.args.apikey not in Config.admin_api_keys:
            raise e.Unauthorized("Invalid API key")
        logger.info(f"{Config.admin_api_keys[self.args.apikey]} is adding a new user: {user_url}")
        user = database.get_user(user_url)
        if user:
            raise e.BadRequest(f"{user_url} already exists. Please use PATCH to modify it.")
        new_user = threativore.users.create_user(user_url)
        if self.args.tags:
            for t in self.args.tags:
                new_user.set_tag(
                    t["tag"],
                    t["value"], 
                    t.get('flair'), 
                    t.get('expires'),
                )             
        if self.args.roles:
            for role in self.args.roles:
                new_user.add_role(UserRoleTypes[role.upper()])
        
        
    patch_parser = reqparse.RequestParser()
    patch_parser.add_argument("apikey", type=str, required=True, help="A threativore admin key.", location='headers')
    patch_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")
    patch_parser.add_argument(
            "tags",
            type=list,
            required=False,
            help="User tags to assign to this user.",
            location="json",
        )
    patch_parser.add_argument(
            "roles",
            type=list,
            required=False,
            help="List of roles to set for this user.",
            location="json",
        )
    patch_parser.add_argument(
            "delete_unspecified_values",
            type=bool,
            required=False,
            default=False,
            help="If set to true, will delete all tags and roles not specified in their respective dict and lists. Setting this to True with non-existent key, will delete all tags/roles",
            location="json",
        )
    
    @api.expect(patch_parser, models.response_model_model_User_patch, validate=True)
    @api.marshal_with(models.response_model_model_User_get, code=200, description='Modify existing user', skip_none=True)
    @api.response(400, 'Bad Request', models.response_model_error)
    @api.response(401, 'Invalid API Key', models.response_model_error)
    @api.response(403, 'Access Denied', models.response_model_error)
    def patch(self,username):
        '''Adds a new user to threativore
        '''
        self.args = self.patch_parser.parse_args()
        user_url = utils.username_to_url(username)
        if self.args.apikey not in Config.admin_api_keys:
            logger.info(self.args.apikey)
            logger.info(Config.admin_api_keys)
            raise e.Unauthorized("Invalid API key")
        logger.info(f"{Config.admin_api_keys[self.args.apikey]} is modifying a user: {user_url}")
        user = database.get_user(user_url)
        logger.debug(self.args.tags)
        if not user:
            raise e.BadRequest(f"{user_url} does not exist. Please use PUT to add it.")
        if self.args.delete_unspecified_values:
            for user_tag in user.tags:
                if user_tag.tag not in [t["tag"] for t in self.args.tags]:
                    logger.debug(f"Removing tag: {user_tag.tag}")
                    user.remove_tag(user_tag.tag)
            for user_role in user.roles:
                try:
                    if user_role.user_role not in [UserRoleTypes[ur.upper()] for ur in self.args.roles]:
                        user.remove_role(user_role.user_role)
                except KeyError:
                    raise e.BadRequest(f"Invalid role in {self.args.roles}")
        if self.args.tags:
            for t in self.args.tags:
                user.set_tag(
                    t["tag"],
                    t["value"], 
                    t.get('flair'), 
                    t.get('expires'),
                )
        if self.args.roles:
            for role in self.args.roles:
                user.add_role(UserRoleTypes[role.upper()])
        return user.get_details(),200
        

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("apikey", type=str, required=True, help="A threativore admin key.", location='headers')
    delete_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")

    @api.expect(delete_parser)
    @api.marshal_with(models.response_model_simple_response, code=200, description='Modify existing user', skip_none=True)
    @api.response(400, 'Bad Request', models.response_model_error)
    @api.response(401, 'Invalid API Key', models.response_model_error)
    @api.response(403, 'Access Denied', models.response_model_error)
    def delete(self,username):
        '''Adds a new user to threativore
        '''
        self.args = self.delete_parser.parse_args()
        user_url = utils.username_to_url(username)
        if self.args.apikey not in Config.admin_api_keys:
            raise e.Unauthorized("Invalid API key")
        logger.info(f"{Config.admin_api_keys[self.args.apikey]} is deleting a user: {user_url}")
        user = database.get_user(user_url)
        if user:
            db.session.delete(user)
            db.session.commit()
        return {"message":"OK."},200