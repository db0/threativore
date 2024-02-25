import time

from loguru import logger

from threativore import threativore
from threativore.flask import APP

if __name__ == "__main__":
    with APP.app_context():
        while True:
            try:
                threativore.check_pms()
                threativore.check_posts()
                threativore.check_comments()
                threativore.resolve_reports()
                time.sleep(5)
            except Exception as err:
                logger.warning(f"Exception during loop: {err}. Will continue after sleep...")
                time.sleep(1)
