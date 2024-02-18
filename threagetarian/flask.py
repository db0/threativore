import os

from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from loguru import logger
from werkzeug.middleware.proxy_fix import ProxyFix

cache = None
APP = Flask(__name__)
APP.wsgi_app = ProxyFix(APP.wsgi_app, x_for=1)

SQLITE_MODE = os.getenv("USE_SQLITE", "1") == "1"

if SQLITE_MODE:
    logger.warning("Using SQLite for database")
    APP.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///threagetarian.db"
else:
    APP.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://postgres:{os.getenv('POSTGRES_PASS')}@{os.getenv('POSTGRES_URL')}"
    APP.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 50,
        "max_overflow": -1,
        # "pool_pre_ping": True,
    }
APP.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(APP)

if not SQLITE_MODE:
    with APP.app_context():
        logger.warning(f"pool size = {db.engine.pool.size()}")
logger.init_ok("Threagitarian Database", status="Started")

# Allow local workstation run
if cache is None:
    cache_config = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300}
    cache = Cache(config=cache_config)
    cache.init_app(APP)
    logger.init_warn("Flask Cache", status="SimpleCache")
