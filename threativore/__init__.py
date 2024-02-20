from dotenv import load_dotenv

from .lemmy import BaseLemmy
from .logger import logger
from .threativore import Threativore

load_dotenv()

base_lemmy = BaseLemmy()
threativore = Threativore(base_lemmy)
logger.init_ok("Threativore", status="Initiated")
