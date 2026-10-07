# One-time migration from the old data.py + lastMessage.pkl setup to
# .env + players.toml + data/state.json. Run once from the project root, then
# delete this file along with data.py and lastMessage.pkl.
#
#   python migrate_data.py

import json
import os
import pickle
import time

import requests

import data
from riotApiConstants import LOL_AMERICA_REGION_URL

ENV_FILENAME = ".env"
PLAYERS_FILENAME = "players.toml"
STATE_FILENAME = "./data/state.json"
OLD_STATE_FILENAME = "lastMessage.pkl"

def main():
    for filename in [ENV_FILENAME, PLAYERS_FILENAME, STATE_FILENAME]:
        if os.path.exists(filename):
            print(f"{filename} already exists, not overwriting anything. Delete it to rerun.")
            return

    # State first since it's the step that hits the Riot API and can fail
    write_state()
    write_players()
    write_env()
    print("Done. Add discord_id lines to players.toml when you're ready for role sync.")

def write_env():
    env = {
        "RIOT_API_KEY": data.RIOT_API_KEY,
        "DISCORD_BOT_TOKEN": data.DISCORD_BOT_KEY.removeprefix("Bot "),
        "DISCORD_CHANNEL_ID": data.DISCORD_CHANNEL_ID,
        "NEWS_CHANNEL_ID": data.NEWS_CHANNEL_ID,
        "HOST_USER_ID": data.HOST_USER_ID,
        "PERSONAL_EMAIL": data.PERSONAL_EMAIL,
        "PROJECT_EMAIL": data.PROJECT_EMAIL,
        "PROJECT_EMAIL_APP_PASSWORD": data.PROJECT_EMAIL_APP_PASSWORD,
    }
    if hasattr(data, "SQLITE_PATH"):
        env["SQLITE_PATH"] = data.SQLITE_PATH

    with open(ENV_FILENAME, "w", encoding="utf-8") as envFile:
        for key, value in env.items():
            envFile.write(f'{key}="{value}"\n')
    print(f"Wrote {ENV_FILENAME}")

def write_players():
    with open(PLAYERS_FILENAME, "w", encoding="utf-8") as playersFile:
        playersFile.write("# One [[player]] block per person. discord_id is optional.\n")
        for name, tag in zip(data.FRIENDS_GAME_NAMES, data.FRIENDS_TAG_LINE):
            playersFile.write(f'\n[[player]]\nriot_id = "{name}#{tag}"\n')
    print(f"Wrote {PLAYERS_FILENAME} with {len(data.FRIENDS_GAME_NAMES)} players")

# Carries the last posted ranks over so the first run still shows arrows.
def write_state():
    old_players = {}
    if os.path.exists(OLD_STATE_FILENAME):
        with open(OLD_STATE_FILENAME, "rb") as lastMessageFile:
            old_players = {p.playerName: p for p in pickle.load(lastMessageFile)}

    state = {}
    for name, tag in zip(data.FRIENDS_GAME_NAMES, data.FRIENDS_TAG_LINE):
        response = requests.get(f"{LOL_AMERICA_REGION_URL}/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers={"X-Riot-Token": data.RIOT_API_KEY})
        response.raise_for_status()
        puuid = response.json()["puuid"]

        state[puuid] = {"riot_id": f"{name}#{tag}"}
        if name in old_players:
            old = old_players[name]
            state[puuid].update(tier=old.playerTier, rank=old.playerRank, lp=old.playerLP)
        time.sleep(.1)

    os.makedirs(os.path.dirname(STATE_FILENAME), exist_ok=True)
    with open(STATE_FILENAME, "w", encoding="utf-8") as stateFile:
        json.dump(state, stateFile, indent=2)
    print(f"Wrote {STATE_FILENAME} ({len(old_players)} players carried over from {OLD_STATE_FILENAME})")

if __name__ == "__main__":
    main()
