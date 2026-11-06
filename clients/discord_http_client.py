import logging

from requests import RequestException, post

from config import DISCORD_BOT_KEY, DISCORD_CHANNEL_ID, HOST_USER_ID, NEWS_CHANNEL_ID

LOG = logging.getLogger("discordHTTPClient")
DISCORD_API_URL = "https://discord.com/api"


# this is more narrow than is optimal, but keeps things clean for our purpose
def messageRankedRaceChannel(message):
    # some sort of message validation here? make sure string if not raise arg exception?

    response = post(
        f"{DISCORD_API_URL}/v10/channels/{DISCORD_CHANNEL_ID}/messages",
        headers={"Authorization": f"{DISCORD_BOT_KEY}"},
        json={"content": message, "tts": "false"},
        timeout=10,
    )
    response.raise_for_status()
    LOG.info(response)

    return response


def messageNewsChannel(content):
    LOG.info(f"Posting message to discord {content}")
    response = post(
        f"{DISCORD_API_URL}/v10/channels/{NEWS_CHANNEL_ID}/messages",
        headers={"Authorization": f"{DISCORD_BOT_KEY}"},
        json={"tts": False, **content},
        timeout=10,
    )
    response.raise_for_status()
    LOG.info(response)

    return response


# content is either message text or a full message payload (for embeds etc.)
def messageHost(content):
    payload = content if isinstance(content, dict) else {"content": content}
    try:
        # Attempting to open channel with host user
        dmResponse = post(
            f"{DISCORD_API_URL}/v10/users/@me/channels",
            headers={"Authorization": f"{DISCORD_BOT_KEY}"},
            json={"recipient_id": HOST_USER_ID},
            timeout=10,
        )
        dmResponse.raise_for_status()

        # Sending message to host user
        dmResponse = post(
            f"{DISCORD_API_URL}/v10/channels/{dmResponse.json()['id']}/messages",
            headers={"Authorization": f"{DISCORD_BOT_KEY}"},
            json={"tts": False, **payload},
            timeout=10,
        )
        dmResponse.raise_for_status()
    except RequestException:
        pass
