from dotenv import load_dotenv

from .lemmy import BaseLemmy
from .logger import logger
from .threativore import Threativore
from .consts import THREATIVORE_VERSION

load_dotenv()

base_lemmy = BaseLemmy()
threativore = Threativore(base_lemmy)
logger.init_ok(f"Threadivore {THREATIVORE_VERSION}", status="Started")
