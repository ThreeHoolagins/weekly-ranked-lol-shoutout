import traceback
import requests
import pickle
import os
import time
import logging
from datetime import datetime
from data import FRIENDS_GAME_NAMES, FRIENDS_TAG_LINE, DISCORD_CHANNEL_ID, HOST_USER_ID
from discordApiConstants import DISCORD_API_URL
from emailPage import PageError
from ranked_player import ranked_player
from riotApiConstants import LOL_AMERICA_REGION_URL, LOL_NA1_PLATFORM_API_URL

LAST_RUN_FILENAME = "lastMessage.pkl"

class RiotApiFailedException(Exception):
    pass

def storeData(sorted_players):
    with open(LAST_RUN_FILENAME, "wb") as lastMessageFile:
        pickle.dump(sorted_players, lastMessageFile)

def loadData():
    db = []
    if os.path.exists(LAST_RUN_FILENAME):
        with open(LAST_RUN_FILENAME, "rb") as lastMessageFile:
            db = pickle.load(lastMessageFile)
        
    return db

def has_data_changed(new_players, old_players):
    if not old_players:
        return bool(new_players)
    old_by_name = {p.playerName: p for p in old_players}
    new_by_name = {p.playerName: p for p in new_players}
    for name, player in new_by_name.items():
        if name not in old_by_name or player != old_by_name[name]:
            return True
    for name in old_by_name:
        if name not in new_by_name:
            return True
    return False

def describe_changes(new_players, old_players):
    lines = []
    old_by_name = {p.playerName: p for p in old_players}
    new_by_name = {p.playerName: p for p in new_players}
    all_names = sorted(set(old_by_name) | set(new_by_name))
    for name in all_names:
        old_p = old_by_name.get(name)
        new_p = new_by_name.get(name)
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

def generateMessage(timestamp, sorted_players, unranked_players):
    
    message = f"## <:questionping:1067913788709421098> Ranked Race Status as of {timestamp} <:questionping:1067913788709421098>\n```"
    message += "\n"
    for player in sorted_players:
        message += player.__repr__(sorted_players[0].find_player_value())

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

def dmHost(discord_bot_api_key, content):
    try:
        dm_response = requests.post(f"{DISCORD_API_URL}/v10/users/@me/channels",
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"recipient_id": HOST_USER_ID})
        dm_response.raise_for_status()
        requests.post(f"{DISCORD_API_URL}/v10/channels/{dm_response.json()['id']}/messages",
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"content": content, "tts": False})
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
    peopleIds = []
    
    try:
        for i in range(0, FRIENDS_GAME_NAMES.__len__()):
            url = f"{LOL_AMERICA_REGION_URL}/riot/account/v1/accounts/by-riot-id/{FRIENDS_GAME_NAMES[i]}/{FRIENDS_TAG_LINE[i]}"
            response = requests.get(url, headers=riot_api_headers)
            response.raise_for_status()
            peopleIds.append(response.json())
            if (debugFlag):
                LOG.debug(peopleIds[i])
            time.sleep(.1)
            
        friendsArr = []
        unranked_players = []
            
        for i in range(0, peopleIds.__len__()):
            url = f"{LOL_NA1_PLATFORM_API_URL}/lol/league/v4/entries/by-puuid/{peopleIds[i]['puuid']}"
            response = requests.get(url, headers=riot_api_headers)
            response.raise_for_status()
            obj = response.json()
            
            if (debugFlag):
                LOG.debug(obj)
            if (obj.__len__() == 0):
                unranked_players.append(FRIENDS_GAME_NAMES[i])
            else:
                friendsArr.append(ranked_player(FRIENDS_GAME_NAMES[i], obj[0]['tier'], obj[0]['rank'], obj[0]['leaguePoints']))
            time.sleep(.1)
            
        sorted_players = sorted(friendsArr)
        curr_timestamp = getTimeStamp()
        
        last_sorted_players = loadData()
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
            
            message = generateMessage(curr_timestamp, sorted_players, unranked_players)
            LOG.debug(f"--- Generated message ---\n{message}")
            dmHost(discord_bot_api_key, message)

        if (not debugFlag and changed):
            message = generateMessage(curr_timestamp, sorted_players, unranked_players)
            response = requests.post(f"{DISCORD_API_URL}/v10/channels/{DISCORD_CHANNEL_ID}/messages", 
                headers={"Authorization": f"{discord_bot_api_key}"},
                json={"content": message, "tts": "false"})         
            response.raise_for_status()
            storeData(sorted_players)
            LOG.info(response)
            return 1
            
            
        return -1
        
    except requests.exceptions.RequestException as e:
        LOG.error("Error: ", e, e.strerror)
        PageError(traceback.format_exc())
        return 0
