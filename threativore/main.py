from threativore.lemmy import base_lemmy
from threativore.threativore import Threativore
from threativore.consts import THREATIVORE_VERSION
from loguru import logger

threativore = Threativore(base_lemmy)
logger.init_ok(f"Threadivore {THREATIVORE_VERSION}", status="Started")
