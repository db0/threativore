import requests
import os

def webhook_parser(message: str):
    if os.getenv("DISCORDWEBHOOK") != "None":
        post_discord_webhook(url=os.getenv("DISCORDWEBHOOK"), message=message,username=None, avatar_url=None)

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
    