import os

from dotenv import load_dotenv

# Secrets and server settings live in .env (see .env.example).
load_dotenv()

RIOT_API_KEY = os.environ["RIOT_API_KEY"]

# The raw bot token. Discord REST calls need it prefixed with "Bot ".
DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_BOT_KEY = f"Bot {DISCORD_BOT_TOKEN}"

# The channel to post the ranked summary in
DISCORD_CHANNEL_ID = os.environ["DISCORD_CHANNEL_ID"]
# The channel to post the patches to
NEWS_CHANNEL_ID = os.environ["NEWS_CHANNEL_ID"]
# Who gets the debug DMs
HOST_USER_ID = os.environ["HOST_USER_ID"]

# Used for which email to send to
PERSONAL_EMAIL = os.environ["PERSONAL_EMAIL"]
# Used for which email to send from, you need to setup an app password
# This is setup for gmail
PROJECT_EMAIL = os.environ["PROJECT_EMAIL"]
PROJECT_EMAIL_APP_PASSWORD = os.environ["PROJECT_EMAIL_APP_PASSWORD"]
