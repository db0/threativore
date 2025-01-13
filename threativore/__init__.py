from dotenv import load_dotenv
import socket
import hashlib
from threativore.logger import logger

load_dotenv()

from threativore.apis import apiv1
from threativore.flask import APP
from threativore.consts import THREATIVORE_VERSION
from threativore.argparser import args
from threativore.routes import * 

APP.register_blueprint(apiv1)

@APP.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, PUT, DELETE, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, apikey, Client-Agent, X-Fields"
    response.headers["Fediseer-Node"] = f"{socket.gethostname()}:{args.port}:{THREATIVORE_VERSION}"
    try:
        etag = hashlib.sha1(response.get_data()).hexdigest()
    except RuntimeError:
        etag = "Runtime Error"
    response.headers["ETag"] = etag
    return response
