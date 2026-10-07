import traceback
import requests
import json
import os
import time
import tomllib
import logging
from datetime import datetime
from config import DISCORD_CHANNEL_ID, HOST_USER_ID
from discordApiConstants import DISCORD_API_URL
from emailPage import PageError
from ranked_player import ranked_player
from riotApiConstants import LOL_AMERICA_REGION_URL, LOL_NA1_PLATFORM_API_URL

PLAYERS_FILENAME = "players.toml"
STATE_FILENAME = "./data/state.json"

class RiotApiFailedException(Exception):
    pass

# state.json is written by the job, never by hand. It's keyed by puuid so
# history survives Riot ID changes, and it caches puuids to skip account lookups:
# { puuid: { "riot_id": "Name#Tag", "tier": ..., "rank": ..., "lp": ... } }
# Unranked players only have "riot_id".
def storeState(state):
    with open(STATE_FILENAME, "w", encoding="utf-8") as stateFile:
        json.dump(state, stateFile, indent=2)

def loadState():
    if not os.path.exists(STATE_FILENAME):
        return {}
    with open(STATE_FILENAME, "r", encoding="utf-8") as stateFile:
        return json.load(stateFile)

def rankedPlayersFromState(state):
    return [ranked_player(puuid, entry["riot_id"].split("#")[0], entry["tier"], entry["rank"], entry["lp"])
            for puuid, entry in state.items() if "tier" in entry]

def has_data_changed(new_players, old_players):
    if not old_players:
        return bool(new_players)
    old_by_id = {p.puuid: p for p in old_players}
    new_by_id = {p.puuid: p for p in new_players}
    for puuid, player in new_by_id.items():
        if puuid not in old_by_id or player != old_by_id[puuid]:
            return True
    for puuid in old_by_id:
        if puuid not in new_by_id:
            return True
    return False

def describe_changes(new_players, old_players):
    lines = []
    old_by_id = {p.puuid: p for p in old_players}
    new_by_id = {p.puuid: p for p in new_players}
    all_players = sorted(({**old_by_id, **new_by_id}).items(), key=lambda item: item[1].playerName)
    for puuid, player in all_players:
        old_p = old_by_id.get(puuid)
        new_p = new_by_id.get(puuid)
        name = player.playerName
        if old_p is None:
            lines.append(f"  {name}: NEW (was unranked/absent)")
        elif new_p is None:
            lines.append(f"  {name}: REMOVED (now unranked/absent, was {old_p.playerTier} {old_p.playerRank} {old_p.playerLP} LP)")
        elif old_p != new_p:
            lines.append(f"  {name}: CHANGED (was {old_p.playerTier} {old_p.playerRank} {old_p.playerLP} LP, now {new_p.playerTier} {new_p.playerRank} {new_p.playerLP} LP)")
        else:
            lines.append(f"  {name}: unchanged ({new_p.playerTier} {new_p.playerRank} {new_p.playerLP} LP)")
    return "\n".join(lines)

def getTimeStamp():
    now = datetime.now()
    day_with_suffix = get_day_with_suffix(now.day)
    return now.strftime(f"%B {day_with_suffix} %Y at %H:%M:%S")

def generateMessage(timestamp, sorted_players, unranked_players, last_sorted_players=None):
    
    message = f"## <:questionping:1067913788709421098> Ranked Race Status as of {timestamp} <:questionping:1067913788709421098>\n```ansi\n"
    
    old_by_id = {p.puuid: p for p in (last_sorted_players or [])}

    for player in sorted_players:
        message += player.__repr__(sorted_players[0].find_player_value(), old_by_id.get(player.puuid))

    unranked_players.sort()
    if len(unranked_players) > 0:
        message += "\n"

    if len(unranked_players) > 2:
        message += ", and ".join(unranked_players) + " are all unranked!\n"
    elif len(unranked_players) > 1:
        message += " and ".join(unranked_players) + " are all unranked!\n"
    elif len(unranked_players) == 1:
        message += unranked_players[0] + " is unranked!\n"
    
    message += "```"
    
    return message

def get_day_with_suffix(day):
    if 11 <= day <= 13:
        return f"{day}th"
    else:
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        return f"{day}{suffixes.get(day % 10, 'th')}"

# content is either message text or a full message payload (for embeds etc.)
def dmHost(discord_bot_api_key, content):
    payload = content if isinstance(content, dict) else {"content": content}
    try:
        dm_response = requests.post(f"{DISCORD_API_URL}/v10/users/@me/channels",
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"recipient_id": HOST_USER_ID})
        dm_response.raise_for_status()
        requests.post(f"{DISCORD_API_URL}/v10/channels/{dm_response.json()['id']}/messages",
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"tts": False, **payload})
    except requests.exceptions.RequestException:
        pass

def messageGroup(riot_api_key, discord_bot_api_key, debugFlag):
    LOG = logging.getLogger("rankedRaceMessageJob")
    
    riot_api_headers = {
        "X-Riot-Token": riot_api_key,
        "Accept-Language" : "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }

    try:
        with open(PLAYERS_FILENAME, "rb") as playersFile:
            players = tomllib.load(playersFile)["player"]

        last_state = loadState()
        cached_puuids = {entry["riot_id"]: puuid for puuid, entry in last_state.items()}
        new_state = {}
        friendsArr = []
        unranked_players = []

        for player in players:
            riot_id = player["riot_id"]
            game_name, tag_line = riot_id.split("#")

            puuid = cached_puuids.get(riot_id)
            if puuid is None:
                url = f"{LOL_AMERICA_REGION_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
                response = requests.get(url, headers=riot_api_headers)
                response.raise_for_status()
                puuid = response.json()["puuid"]
                if (debugFlag):
                    LOG.debug(response.json())
                time.sleep(.1)

            url = f"{LOL_NA1_PLATFORM_API_URL}/lol/league/v4/entries/by-puuid/{puuid}"
            response = requests.get(url, headers=riot_api_headers)
            response.raise_for_status()
            obj = response.json()

            if (debugFlag):
                LOG.debug(obj)
            new_state[puuid] = {"riot_id": riot_id}
            if (obj.__len__() == 0):
                unranked_players.append(game_name)
            else:
                friendsArr.append(ranked_player(puuid, game_name, obj[0]['tier'], obj[0]['rank'], obj[0]['leaguePoints']))
                new_state[puuid].update(tier=obj[0]['tier'], rank=obj[0]['rank'], lp=obj[0]['leaguePoints'])
            time.sleep(.1)

        sorted_players = sorted(friendsArr)
        curr_timestamp = getTimeStamp()

        last_sorted_players = rankedPlayersFromState(last_state)
        if debugFlag and len(sorted_players) > 0:
            sorted_players[0].playerLP += 1
            if len(sorted_players) > 1:
                sorted_players[-1].playerLP -= 1
            LOG.debug("--- Debug LP manipulation applied (top +1, bottom -1) ---")
        changed = has_data_changed(sorted_players, last_sorted_players)

        if debugFlag:
            LOG.debug("--- New player data ---")
            for p in sorted_players:
                LOG.debug(f"  {p.playerName}: {p.playerTier} {p.playerRank} {p.playerLP} LP")
            LOG.debug("--- Old player data ---")
            for p in last_sorted_players:
                LOG.debug(f"  {p.playerName}: {p.playerTier} {p.playerRank} {p.playerLP} LP")
            LOG.debug(f"--- Changes detected: {changed} ---")
            LOG.debug("\n" + describe_changes(sorted_players, last_sorted_players))
            
            message = generateMessage(curr_timestamp, sorted_players, unranked_players, last_sorted_players)
            LOG.debug(f"--- Generated message ---\n{message}")
            dmHost(discord_bot_api_key, message)

        if (not debugFlag and changed):
            message = generateMessage(curr_timestamp, sorted_players, unranked_players, last_sorted_players)
            response = requests.post(f"{DISCORD_API_URL}/v10/channels/{DISCORD_CHANNEL_ID}/messages", 
                headers={"Authorization": f"{discord_bot_api_key}"},
                json={"content": message, "tts": "false"})         
            response.raise_for_status()
            storeState(new_state)
            LOG.info(response)
            return 1

        # Nothing to post, but still save so new puuids and renames get cached
        if (not debugFlag):
            storeState(new_state)

        return -1
        
    except requests.exceptions.RequestException as e:
        LOG.error("Error: ", e, e.strerror)
        PageError(traceback.format_exc())
        return 0
