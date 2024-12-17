import requests
from threativore.config import Config

from loguru import logger

def webhook_parser(message: str):
    if Config.discordwebhook is not None and Config.discordwebhook != "None" and Config.discordwebhook != "":
        if not post_discord_webhook(url=Config.discordwebhook, message=message,username=None, avatar_url=None):
            logger.debug("Discord webhook failed")
            
    if Config.slackwebhook is not None and Config.slackwebhook != "None" and Config.slackwebhook != "":
        if post_slack_webhook(url=Config.slackwebhook, message=message):
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