import logging
import time

from requests import get

from config import RIOT_API_KEY
from riotApiConstants import LOL_AMERICA_REGION_URL, LOL_NA1_PLATFORM_API_URL

riot_api_headers = {
    "X-Riot-Token": RIOT_API_KEY,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://developer.riotgames.com",
}

LOG = logging.getLogger("riot_developer_api_client")


class RiotApiFailedException(Exception):
    pass


def getPUUIDByGameName(gameName, tagLine, debugFlag):
    url = f"{LOL_AMERICA_REGION_URL}/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"

    response = get(url, headers=riot_api_headers, timeout=10)
    response.raise_for_status()

    if debugFlag:
        LOG.debug(response.json())
    time.sleep(0.1)

    return response.json()["puuid"]


def getPlayerRankedData(puuid):
    url = f"{LOL_NA1_PLATFORM_API_URL}/lol/league/v4/entries/by-puuid/{puuid}"

    response = get(url, headers=riot_api_headers, timeout=10)
    response.raise_for_status()

    return response.json()
