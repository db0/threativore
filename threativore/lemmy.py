import threading
import time
from loguru import logger
from pythorhead import Lemmy
from threativore.config import Config


class BaseLemmy:
    def __init__(self):
        lemmy_domain = Config.lemmy_domain
        lemmy_username = Config.lemmy_username
        lemmy_password = Config.lemmy_password
        self.lemmy = Lemmy(f"https://{lemmy_domain}")
        self.lemmy.log_in(lemmy_username, lemmy_password)
        self.login_refresh_thread = threading.Thread(target=self.ensure_fresh_login, args=(), daemon=True)
        self.login_refresh_thread.start()

    def ensure_fresh_login(self):
        while True:
            time.sleep(3600*24)
            logger.debug("24 hours passed. Refreshing lemmy login credentials.")
            self.lemmy.relog_in()
        
