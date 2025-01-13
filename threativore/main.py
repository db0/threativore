from threativore.lemmy import BaseLemmy
from threativore.threativore import Threativore
from threativore.consts import THREATIVORE_VERSION
from loguru import logger

base_lemmy = BaseLemmy()
threativore = Threativore(base_lemmy)
logger.init_ok(f"Threadivore {THREATIVORE_VERSION}", status="Started")
