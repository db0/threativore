import time

from loguru import logger

from threagetarian import threagetarian
from threagetarian.flask import APP

if __name__ == "__main__":
    with APP.app_context():
        while True:
            try:
                threagetarian.check_pms()
                threagetarian.check_posts()
                threagetarian.check_comments()
                threagetarian.resolve_reports()
            except Exception as err:
                logger.warning(f"Exception during loop: {err}. Will continue after sleep...")
                time.sleep(1)
