from dotenv import load_dotenv

from .lemmy import BaseLemmy
from .logger import logger
from .threagetarian import Threagetarian

load_dotenv()

base_lemmy = BaseLemmy()
threagetarian = Threagetarian(base_lemmy)
logger.init_ok("Threagetarian", status="Initiated")
