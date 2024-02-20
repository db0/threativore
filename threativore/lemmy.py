import os

from pythorhead import Lemmy


class BaseLemmy:
    def __init__(self):
        lemmy_domain = os.environ["LEMMY_DOMAIN"]
        lemmy_username = os.environ["LEMMY_USERNAME"]
        lemmy_password = os.environ["LEMMY_PASSWORD"]
        self.lemmy = Lemmy(f"https://{lemmy_domain}")
        self.lemmy.log_in(lemmy_username, lemmy_password)
