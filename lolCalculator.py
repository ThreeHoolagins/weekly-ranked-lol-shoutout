import time
from datetime import datetime
import requests

from data import RIOT_API_KEY
from riotApiConstants import LOL_AMERICA_REGION_URL, LOL_NA1_PLATFORM_API_URL

class lolCalculator:
    
    def findRankedWinRate(gameName, tagLine):
        #something here
        puuid = lolCalculator.findPuuid(gameName, tagLine)
        time.sleep(1.2)
        return lolCalculator.findWinRate(puuid, "ranked")
        
    def findWinRate(puuid, QueueType):
        games = []
        start = 0
        startOfYear = int(datetime(2025, 1, 5).timestamp())
        while True:
            response = requests.get(f"{LOL_AMERICA_REGION_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count=100&startTime={startOfYear}&type={QueueType}&api_key={RIOT_API_KEY}")
            time.sleep(1.2)
            response.raise_for_status()
            
            games.extend(response.json())
            
            if (len(response.json()) < 100):
                break
            
            start += 100
            
        print(f"{len(games)} games found")
        gamesWon = 0
        totalGames = 0
        for game in games:
            response = requests.get(f"{LOL_AMERICA_REGION_URL}/lol/match/v5/matches/{game}?api_key={RIOT_API_KEY}")
            time.sleep(1.2)
            response.raise_for_status()
            
            playerPosition = 0
            for playerGamePuuid in response.json()["metadata"]["participants"]:
                if playerGamePuuid == puuid:
                    break
                playerPosition += 1
            
            wasGameWon = response.json()["info"]["participants"][playerPosition]["win"]
            
            totalGames += 1
            if wasGameWon:
                gamesWon += 1
            
        
        return gamesWon / totalGames * 100
        
    def findPuuid(gameName, tagLine):
        response = requests.get(f"{LOL_AMERICA_REGION_URL}/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}?api_key={RIOT_API_KEY}")
        if (response.status_code == 200):
            return response.json()["puuid"]
        else:
            response.raise_for_status()