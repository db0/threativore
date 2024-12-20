import requests
from threativore.config import Config

from loguru import logger

def webhook_parser(message: str):
    if Config.discord_webhook is not None and Config.discord_webhook != "None" and Config.discord_webhook != "":
        if not post_discord_webhook(url=Config.discord_webhook, message=message,username=None, avatar_url=None):
            logger.debug("Discord webhook failed")
            
    if Config.slack_webhook is not None and Config.slack_webhook != "None" and Config.slack_webhook != "":
        if post_slack_webhook(url=Config.slack_webhook, message=message):
            logger.debug("Slack webhook failed")

def post_discord_webhook(url: str, message:str, username:str, avatar_url:str) -> bool:
    if username == None:
        username = "Threativore"
    
    payload = {
        "content": message,
        "username": username,
        "avatar_url": avatar_url
    }

    response = requests.post(url, json=payload)
    if response.status_code == 204:
        return True
    else:
        return False

def post_slack_webhook(url: str, message: str) -> bool:
    payload = {
        "text": message
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return True
    else:
        return False