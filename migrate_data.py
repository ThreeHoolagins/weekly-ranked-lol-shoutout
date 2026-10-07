# One-time migration from the old data.py + lastMessage.pkl setup to
# .env + players.toml + data/state.json. Run from the project root.
#
#   python migrate_data.py            # migrate, backing up the old files first
#   python migrate_data.py rollback   # put the old files back, then `git checkout master`
#
# Migrating never deletes or edits data.py or lastMessage.pkl; it copies them to
# BACKUP_DIR first. Once you're happy on the new setup, delete this file, data.py,
# lastMessage.pkl and the backup folder.

import json
import os
import pickle
import shutil
import sys
import time
import tomllib

import requests

from riotApiConstants import LOL_AMERICA_REGION_URL

ENV_FILENAME = ".env"
PLAYERS_FILENAME = "players.toml"
STATE_FILENAME = "./data/state.json"
OLD_DATA_FILENAME = "data.py"
OLD_STATE_FILENAME = "lastMessage.pkl"
BACKUP_DIR = "./data/pre-migration-backup"

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()

def migrate():
    for filename in [ENV_FILENAME, PLAYERS_FILENAME, STATE_FILENAME]:
        if os.path.exists(filename):
            print(f"{filename} already exists, not overwriting anything. Delete it to rerun.")
            return

    backup_old_files()

    # State first since it's the step that hits the Riot API and can fail
    write_state()
    write_players()
    write_env()
    print("Done. Add discord_id lines to players.toml when you're ready for role sync.")

def backup_old_files():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for filename in [OLD_DATA_FILENAME, OLD_STATE_FILENAME]:
        backup = os.path.join(BACKUP_DIR, filename)
        if os.path.exists(filename) and not os.path.exists(backup):
            shutil.copy2(filename, backup)
            print(f"Backed up {filename} to {backup}")

# Puts data.py back if it's gone, and rebuilds lastMessage.pkl from state.json so
# the old code picks up from the last post made on the new setup instead of
# re-posting or showing stale arrows. The new files are left alone so you can
# check out the branch again later without migrating twice.
def rollback():
    backup_data = os.path.join(BACKUP_DIR, OLD_DATA_FILENAME)
    if not os.path.exists(OLD_DATA_FILENAME):
        if not os.path.exists(backup_data):
            print(f"No {OLD_DATA_FILENAME} and no backup at {backup_data}, can't roll back.")
            return
        shutil.copy2(backup_data, OLD_DATA_FILENAME)
        print(f"Restored {OLD_DATA_FILENAME} from {backup_data}")
    else:
        print(f"{OLD_DATA_FILENAME} still present, leaving it as is")

    if os.path.exists(STATE_FILENAME):
        with open(STATE_FILENAME, "r", encoding="utf-8") as stateFile:
            state = json.load(stateFile)
        old_players = [old_ranked_player(entry) for entry in state.values() if "tier" in entry]
        with open(OLD_STATE_FILENAME, "wb") as lastMessageFile:
            pickle.dump(old_players, lastMessageFile)
        print(f"Rebuilt {OLD_STATE_FILENAME} from {STATE_FILENAME} ({len(old_players)} ranked players)")
    else:
        print(f"No {STATE_FILENAME}, leaving {OLD_STATE_FILENAME} as is")

    warn_about_new_players()
    print("Now run: git checkout master")

# The ranked_player on master has no puuid, so build one with just the old fields.
def old_ranked_player(entry):
    from ranked_player import ranked_player
    player = ranked_player.__new__(ranked_player)
    player.playerName = entry["riot_id"].split("#")[0]
    player.playerTier = entry["tier"]
    player.playerRank = entry["rank"]
    player.playerLP = int(entry["lp"])
    return player

def warn_about_new_players():
    if not os.path.exists(PLAYERS_FILENAME):
        return
    import data
    with open(PLAYERS_FILENAME, "rb") as playersFile:
        riot_ids = [player["riot_id"] for player in tomllib.load(playersFile)["player"]]
    old_riot_ids = [f"{name}#{tag}" for name, tag in zip(data.FRIENDS_GAME_NAMES, data.FRIENDS_TAG_LINE)]
    missing = [riot_id for riot_id in riot_ids if riot_id not in old_riot_ids]
    if missing:
        print(f"Heads up, these are in {PLAYERS_FILENAME} but not {OLD_DATA_FILENAME}: {', '.join(missing)}")

def write_env():
    import data
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

    with open(ENV_FILENAME, "w", encoding="utf-8") as envFile:
        for key, value in env.items():
            envFile.write(f'{key}="{value}"\n')
    print(f"Wrote {ENV_FILENAME}")

def write_players():
    import data
    with open(PLAYERS_FILENAME, "w", encoding="utf-8") as playersFile:
        playersFile.write("# One [[player]] block per person. discord_id is optional.\n")
        for name, tag in zip(data.FRIENDS_GAME_NAMES, data.FRIENDS_TAG_LINE):
            playersFile.write(f'\n[[player]]\nriot_id = "{name}#{tag}"\n')
    print(f"Wrote {PLAYERS_FILENAME} with {len(data.FRIENDS_GAME_NAMES)} players")

# Carries the last posted ranks over so the first run still shows arrows.
def write_state():
    import data
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
