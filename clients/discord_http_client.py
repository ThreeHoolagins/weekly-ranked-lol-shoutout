from requests import post, RequestException 
from config import DISCORD_CHANNEL_ID, NEWS_CHANNEL_ID, HOST_USER_ID, DISCORD_BOT_KEY
import logging

LOG = logging.getLogger("discordHTTPClient")
DISCORD_API_URL = "https://discord.com/api"

# this is more narrow than is optimal, but keeps things clean for our purpose
def message_ranked_race_channel(message):
    #some sort of message validation here? make sure string if not raise arg exception?
    
    response = post(f"{DISCORD_API_URL}/v10/channels/{DISCORD_CHANNEL_ID}/messages", 
                headers={"Authorization": f"{DISCORD_BOT_KEY}"},
                json={"content": message, "tts": "false"})
    response.raise_for_status()
    LOG.info(response)
    
    return response

def message_news_channel(content):
    LOG.info(f"Posting message to discord {content}")
    response = post(f"{DISCORD_API_URL}/v10/channels/{NEWS_CHANNEL_ID}/messages",
        headers={"Authorization": f"{DISCORD_BOT_KEY}"},
        json={"tts": False, **content})
    response.raise_for_status()
    LOG.info(response)
    
    return response

# content is either message text or a full message payload (for embeds etc.)
def message_host(content):
    payload = content if isinstance(content, dict) else {"content": content}
    try:
        # Attempting to open channel with host user
        dm_response = post(f"{DISCORD_API_URL}/v10/users/@me/channels",
            headers={"Authorization": f"{DISCORD_BOT_KEY}"},
            json={"recipient_id": HOST_USER_ID})
        dm_response.raise_for_status()
        
        # Sending message to host user
        dm_response = post(f"{DISCORD_API_URL}/v10/channels/{dm_response.json()['id']}/messages",
            headers={"Authorization": f"{DISCORD_BOT_KEY}"},
            json={"tts": False, **payload})
        dm_response.raise_for_status()
    except RequestException:
        pass