import requests
import pickle
import os
import time
import logging
from datetime import datetime
from data import FRIENDS_GAME_NAMES, FRIENDS_TAG_LINE, DISCORD_CHANNEL_ID
from ranked_player import ranked_player

API_URL = "https://americas.api.riotgames.com"
API_URL2 = "https://na1.api.riotgames.com"
LAST_RUN_FILENAME = "lastMessage.pkl"

def storeData(sorted_players):
    with open(LAST_RUN_FILENAME, "wb") as lastMessageFile:
        pickle.dump(sorted_players, lastMessageFile)

def loadData():
    db = []
    if os.path.exists(LAST_RUN_FILENAME):
        with open(LAST_RUN_FILENAME, "rb") as lastMessageFile:
            db = pickle.load(lastMessageFile)
        
    return db

def getTimeStamp():
    now = datetime.now()
    day_with_suffix = get_day_with_suffix(now.day)
    return now.strftime(f"%B {day_with_suffix} %Y at %H:%M:%S")

def generateMessage(timestamp, sorted_players, unranked_players):
    
    message = f"## <:questionping:1067913788709421098> Ranked Race Status as of {timestamp} <:questionping:1067913788709421098>\n```"
    message += "\n"
    for player in sorted_players:
        message += player.__repr__()

    unranked_players.sort()
    if len(unranked_players) > 0:
        message += "\n"

    if len(unranked_players) > 2:
        message += ", and ".join(unranked_players) + " are all unranked!\n"
    elif len(unranked_players) > 1:
        message += " and ".join(unranked_players) + " are all unranked!\n"
    else:
        message += unranked_players[0] + " is unranked!\n"
    
    message += "```"
    
    return message

def get_day_with_suffix(day):
    if 11 <= day <= 13:
        return f"{day}th"
    else:
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        return f"{day}{suffixes.get(day % 10, 'th')}"

def messageGroup(riot_api_key, discord_bot_api_key, debugFlag):
    LOG = logging.getLogger("rankedRaceMessageJob")
    
    riot_api_headers = {
        "X-Riot-Token": riot_api_key,
        "Accept-Language" : "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }
    
    peopleIds = []
    summonerIds = []
    
    try:
        for i in range(0, FRIENDS_GAME_NAMES.__len__()):
            url = API_URL + f"/riot/account/v1/accounts/by-riot-id/{FRIENDS_GAME_NAMES[i]}/{FRIENDS_TAG_LINE[i]}"
            peopleIds.append(requests.get(url, headers=riot_api_headers).json())
            if (debugFlag):
                LOG.debug(peopleIds[i])
            time.sleep(.1)
        
        for i in range(0, peopleIds.__len__()):
            url = API_URL2 + f"/lol/summoner/v4/summoners/by-puuid/{peopleIds[i]['puuid']}"
            summonerIds.append(requests.get(url, headers=riot_api_headers).json())
            if (debugFlag):
                LOG.debug(summonerIds[i])
            time.sleep(.1)
            
        friendsArr = []
        unranked_players = []
            
        for i in range(0, summonerIds.__len__()):
            url = API_URL2 + f"/lol/league/v4/entries/by-summoner/{summonerIds[i]['id']}"
            obj = requests.get(API_URL2 + f"/lol/league/v4/entries/by-summoner/{summonerIds[i]['id']}", headers=riot_api_headers).json()
            if (debugFlag):
                LOG.debug(obj)
            if (obj.__len__() == 0):
                unranked_players.append(FRIENDS_GAME_NAMES[i])
            else:
                friendsArr.append(ranked_player(FRIENDS_GAME_NAMES[i], obj[0]['tier'], obj[0]['rank'], obj[0]['leaguePoints']))
            time.sleep(.1)
            
        sorted_players = sorted(friendsArr)
        curr_timestamp = getTimeStamp()
        message = generateMessage(curr_timestamp, sorted_players, unranked_players)
        
        last_sorted_players = loadData()
        last_message = generateMessage(curr_timestamp, last_sorted_players, unranked_players)

        if (debugFlag):
            LOG.debug(message)
            LOG.debug(last_message)
            LOG.debug(f"Match? {last_message == message}")

        if (not debugFlag and message != last_message):
            maybeSuccess = requests.post(f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages", 
                headers={"Authorization": f"{discord_bot_api_key}"},
                json={"content": message, "tts": "false"})             
            storeData(sorted_players)
            LOG.info(maybeSuccess)
            return 1
            
        return -1
        
    except requests.exceptions.RequestException as e:
        LOG.error("Error: ", e, e.strerror)
        return 0