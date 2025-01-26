from flask_restx import Resource, reqparse
from flask import request
from threativore.flask import cache
from loguru import logger
from threativore import database
from threativore import exceptions as e
from threativore.apis.v1.base import *

class OpenVotes(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument("Client-Agent", default="unknown:0:unknown", type=str, required=False, help="The client name and version.", location="headers")

    @api.expect(get_parser)
    # @cache.cached(timeout=600)
    @api.marshal_with(models.response_model_open_votes, code=200, description='Get Open Voting Threads', as_list=True)
    def get(self):
        '''List all current voting threads
        '''
        self.args = self.get_parser.parse_args()        
        return [v.get_details() for v in database.get_open_votes()],200
