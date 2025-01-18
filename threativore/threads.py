import threading
import requests
import csv
from datetime import datetime, timedelta
from threativore.config import Config
from threativore.main import threativore
from threativore import database
from loguru import logger
from threativore.flask import APP
from threativore.emoji import lemmy_emoji

def process_user(data):
    if data.get("visibility") == "secret":
        return
    logger.debug(f"Processing Liberapay patron: {data.get('patron_id')}({data.get('patron_username')})")
    tier = "drinking mate"
    for liberapay_tier in sorted(Config.liberapay_tiers.keys(), key=float, reverse=True):
        if float(data.get("weekly_amount")) >= float(liberapay_tier):
            tier = Config.liberapay_tiers[liberapay_tier]
            logger.debug(f"Found Liberapay tier: {liberapay_tier}. Assigning tier: {tier}")
            break
    user = database.get_user_from_override_email(str(data.get("patron_id")))
    if not user:
        logger.warning(f"Liberapay patron '{data.get('patron_id')}' isn't defined in the overrides!")
        # Temporary. Remove soon.
        user = database.get_user_from_override_email(data.get("patron_username"))
        if not user:
            logger.warning(f"Liberapay patron '{data.get('patron_username')}' isn't defined in the overrides!")
            return    
    user.set_tag(
        tag="liberapay_tier", 
        value=tier,
        custom_emoji=tier.replace(r' ','_'),
        expires=datetime.utcnow() + timedelta(days=Config.donation_expiration_days),
    )
    tier_markdown = lemmy_emoji.get_emoji_markdown(tier.replace(r' ','_'))
    pledge_date = datetime.strptime(data.get("pledge_date"), "%Y-%m-%d")
    if pledge_date > datetime.utcnow() - timedelta(days=7):
      threativore.reply_to_user_url(
          user_url=user.user_url, 
          message=(
              'Arr matey! Your donation to the ![a pirate chest full of doubloons](https://lemmy.dbzer0.com/pictrs/image/af140ff3-a09d-4b9c-8907-15d34d674c0e.png "booty") is acknowledged and will go towards '
              "the upkeep of the ship. "
              f'You have been marked as a {tier_markdown}{tier}{tier_markdown}'
              'Thank ye! ![pirate captain giving the thumbs up](https://lemmy.dbzer0.com/pictrs/image/bc10b52a-196d-4e4a-98a2-bfd2dbb10d9a.png "thumbsup")'
          )
      )
    
def download_and_parse_csv():
    url = f'https://liberapay.com/{Config.liberapay_username}/patrons/export.csv?scope=active'
    cookies = {'session': Config.liberapay_cookie}
    response = requests.get(url, cookies=cookies)
    response.raise_for_status()  # Ensure we notice bad responses

    csv_content = response.text
    csv_reader = csv.DictReader(csv_content.splitlines())
    data = [row for row in csv_reader]
    for row in data:
        process_user(row)

def schedule_weekly_download():
    if not Config.liberapay_username:
        return
    if not Config.liberapay_cookie:
        return
    logger.init("liberapay hourly download thread", status="Running")
    with APP.app_context():
        try:
            download_and_parse_csv()
        except requests.exceptions.HTTPError as err:
            logger.error(f"Could not download the liberapay usernames: {err}")
            raise err
    next_run = datetime.now() + timedelta(hours=1)
    delay = (next_run - datetime.now()).total_seconds()
    timer = threading.Timer(delay, schedule_weekly_download)
    timer.daemon = True  # Set the thread as a daemon
    timer.start()

