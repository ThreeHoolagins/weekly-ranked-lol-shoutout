import requests
import time
from datetime import datetime
from data import FRIENDS_GAME_NAMES, FRIENDS_TAG_LINE, DISCORD_CHANNEL_ID
from ranked_player import ranked_player

API_URL = "https://americas.api.riotgames.com"
API_URL2 = "https://na1.api.riotgames.com"


def get_day_with_suffix(day):
    if 11 <= day <= 13:
        return f"{day}th"
    else:
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        return f"{day}{suffixes.get(day % 10, 'th')}"

def messageGroup(riot_api_key, discord_bot_api_key, debugFlag):
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
                print(peopleIds[i])
            time.sleep(.1)
        
        if (debugFlag):
            print()
        
        for i in range(0, peopleIds.__len__()):
            url = API_URL2 + f"/lol/summoner/v4/summoners/by-puuid/{peopleIds[i]['puuid']}"
            summonerIds.append(requests.get(url, headers=riot_api_headers).json())
            if (debugFlag):
                print(summonerIds[i])
            time.sleep(.1)
            
        if (debugFlag):
            print()
            
        now = datetime.now()
        day_with_suffix = get_day_with_suffix(now.day)
        current_datetime = now.strftime(f"%B {day_with_suffix} %Y at %H:%M:%S")
        message = f"## <:questionping:1067913788709421098> Ranked Race Status as of {current_datetime} <:questionping:1067913788709421098>\n```"
        friendsArr = []
            
        for i in range(0, summonerIds.__len__()):
            url = API_URL2 + f"/lol/league/v4/entries/by-summoner/{summonerIds[i]['id']}"
            obj = requests.get(API_URL2 + f"/lol/league/v4/entries/by-summoner/{summonerIds[i]['id']}", headers=riot_api_headers).json()
            if (debugFlag):
                print(obj)
            if (obj.__len__() == 0):
                friendsArr.append(ranked_player(FRIENDS_GAME_NAMES[i], "UNRANKED", "UNRANKED", 0))
            else:
                friendsArr.append(ranked_player(FRIENDS_GAME_NAMES[i], obj[0]['tier'], obj[0]['rank'], obj[0]['leaguePoints']))
            time.sleep(.1)
            
        if (debugFlag):
            print()
            
        message += "\n"
        sorted_players = sorted(friendsArr)
        for player in sorted_players:
            message += player.__repr__()

        message += "```"
        if (debugFlag):
            print(message)

        if (not debugFlag):
            maybeSuccess = requests.post(f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages", 
                headers={"Authorization": f"{discord_bot_api_key}"},
                json={"content": message, "tts": "false"})
            print(maybeSuccess)
        
    except requests.exceptions.RequestException as e:
        print("Error: ", e, e.strerror)
        return