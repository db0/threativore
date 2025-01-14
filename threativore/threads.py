import threading
import requests
import csv
from datetime import datetime, timedelta
from threativore.config import Config
from threativore.main import threativore
from threativore import database
from loguru import logger
from threativore.flask import APP


def process_user(data):
    if data.get("visibility") == "secret":
        return
    logger.debug(f"Processing Liberapay patron: {data.get('patron_username')}")
    tier = "drinking mate"
    tier_flairs = {
        "powder monkey": "https://lemmy.dbzer0.com/pictrs/image/d9d3a0db-c03a-45d0-a469-aad183cecd9a.webp",
        "buccaneer": "https://lemmy.dbzer0.com/pictrs/image/f4c6e9fb-7576-4d93-beba-af937db36784.webp",
        "threadiverse enjoyer": "https://lemmy.dbzer0.com/pictrs/image/efc716fe-f9bd-48ec-a065-b46dad5aa042.webp",
    }
    if float(data.get("weekly_amount")) > 5:
        tier = "powder monkey"
    elif float(data.get("weekly_amount")) > 1:
        tier = "buccaneer"
    else:
        tier = "threadiverse enjoyer"
    tier_flair = tier_flairs.get(tier.lower(), "")
    user = database.get_user_from_override_email(data.get("patron_username"))
    if not user:
        logger.warning(f"Liberapay patron '{data.get('patron_username')}' isn't defined in the overrides!")
        return    
    user.set_tag(
        tag="liberapay_tier", 
        value=tier,
        flair=tier_flair,
        expires=datetime.utcnow() + timedelta(days=Config.donation_expiration_days),
    )
    pledge_date = datetime.strptime(data.get("pledge_date"), "%Y-%m-%d")
    if pledge_date > datetime.utcnow() - timedelta(days=7):
      threativore.reply_to_user_url(
          user_url=user.user_url, 
          message=(
              'Arr matey! Your donation to the ![a pirate chest full of doubloons](https://lemmy.dbzer0.com/pictrs/image/af140ff3-a09d-4b9c-8907-15d34d674c0e.png "booty") is acknowledged and will go towards '
              "the upkeep of the ship. "
              f'You have been marked as a ![{tier}]({tier_flair} "emoji") {tier} ![{tier}]({tier_flair} "emoji")'
              'Thank ye! ![pirate captain giving the thumbs up](https://lemmy.dbzer0.com/pictrs/image/bc10b52a-196d-4e4a-98a2-bfd2dbb10d9a.png "thumbsup")'
          )
      )
    
def download_and_parse_csv():
    url = 'https://liberapay.com/db0/patrons/export.csv?scope=active'
    cookies = {'session': '1630248:800:9w_-J5CPxKtGvDtsW5R_C1JQQcP3Lemy.ro'}
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
    logger.init("liberapay weekly download thread", status="Running")
    with APP.app_context():
        download_and_parse_csv()
    next_run = datetime.now() + timedelta(weeks=1)
    delay = (next_run - datetime.now()).total_seconds()
    timer = threading.Timer(delay, schedule_weekly_download)
    timer.daemon = True  # Set the thread as a daemon
    timer.start()

