import json
import logging
import os
import time
import tomllib
import traceback
from datetime import datetime

import requests

from clients.discord_http_client import messageHost, messageRankedRaceChannel
from emailPage import PageError
from rankedPlayer import rankedPlayer
from riotApiConstants import LOL_AMERICA_REGION_URL, LOL_NA1_PLATFORM_API_URL

PLAYERS_FILENAME = "./config/players.toml"
STATE_FILENAME = "./data/state/state.json"


class RiotApiFailedException(Exception):
    pass


# state.json is written by the job, never by hand. It's keyed by puuid so
# history survives Riot ID changes, and it caches puuids to skip account lookups:
# { puuid: { "riot_id": "Name#Tag", "tier": ..., "rank": ..., "lp": ... } }  # noqa: ERA001
# Unranked players only have "riot_id".
def storeState(state):
    with open(STATE_FILENAME, "w", encoding="utf-8") as stateFile:
        json.dump(state, stateFile, indent=2)


def loadState():
    if not os.path.exists(STATE_FILENAME):
        return {}
    with open(STATE_FILENAME, encoding="utf-8") as stateFile:
        return json.load(stateFile)


def rankedPlayersFromState(state):
    return [
        rankedPlayer(puuid, entry["riot_id"].split("#")[0], entry["tier"], entry["rank"], entry["lp"])
        for puuid, entry in state.items()
        if "tier" in entry
    ]


def hasDataChanged(newPlayers, oldPlayers):
    if not oldPlayers:
        return bool(newPlayers)
    oldById = {p.puuid: p for p in oldPlayers}
    newById = {p.puuid: p for p in newPlayers}
    for puuid, player in newById.items():
        if puuid not in oldById or player != oldById[puuid]:
            return True
    return any(puuid not in newById for puuid in oldById)


def describeChanges(newPlayers, oldPlayers):
    lines = []
    oldById = {p.puuid: p for p in oldPlayers}
    newById = {p.puuid: p for p in newPlayers}
    allPlayers = sorted(({**oldById, **newById}).items(), key=lambda item: item[1].playerName)
    for puuid, player in allPlayers:
        oldP = oldById.get(puuid)
        newP = newById.get(puuid)
        name = player.playerName
        if oldP is None:
            lines.append(f"  {name}: NEW (was unranked/absent)")
        elif newP is None:
            lines.append(
                f"  {name}: REMOVED (now unranked/absent, was {oldP.playerTier} {oldP.playerRank} {oldP.playerLP} LP)"
            )
        elif oldP != newP:
            lines.append(
                f"  {name}: CHANGED (was {oldP.playerTier} {oldP.playerRank} {oldP.playerLP} LP, "
                f"now {newP.playerTier} {newP.playerRank} {newP.playerLP} LP)"
            )
        else:
            lines.append(f"  {name}: unchanged ({newP.playerTier} {newP.playerRank} {newP.playerLP} LP)")
    return "\n".join(lines)


def getTimeStamp():
    now = datetime.now().astimezone()
    dayWithSuffix = getDayWithSuffix(now.day)
    return now.strftime(f"%B {dayWithSuffix} %Y at %H:%M:%S")


def generateMessage(timestamp, sortedPlayers, unrankedPlayers, lastSortedPlayers=None):

    ping = "<:questionping:1067913788709421098>"
    message = f"## {ping} Ranked Race Status as of {timestamp} {ping}\n```ansi\n"

    oldById = {p.puuid: p for p in (lastSortedPlayers or [])}

    for player in sortedPlayers:
        message += player.__repr__(sortedPlayers[0].findPlayerValue(), oldById.get(player.puuid))

    unrankedPlayers.sort()
    if len(unrankedPlayers) > 0:
        message += "\n"

    if len(unrankedPlayers) > 2:
        message += ", and ".join(unrankedPlayers) + " are all unranked!\n"
    elif len(unrankedPlayers) > 1:
        message += " and ".join(unrankedPlayers) + " are all unranked!\n"
    elif len(unrankedPlayers) == 1:
        message += unrankedPlayers[0] + " is unranked!\n"

    message += "```"

    return message


def getDayWithSuffix(day):
    if 11 <= day <= 13:
        return f"{day}th"
    else:
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        return f"{day}{suffixes.get(day % 10, 'th')}"


def messageGroup(riotApiKey, discordBotApiKey, debugFlag):
    LOG = logging.getLogger("rankedRaceMessageJob")

    riotApiHeaders = {
        "X-Riot-Token": riotApiKey,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com",
    }

    try:
        with open(PLAYERS_FILENAME, "rb") as playersFile:
            players = tomllib.load(playersFile)["player"]

        lastState = loadState()
        cachedPuuids = {entry["riot_id"]: puuid for puuid, entry in lastState.items()}
        newState = {}
        friendsArr = []
        unrankedPlayers = []

        for player in players:
            riotId = player["riot_id"]
            gameName, tagLine = riotId.split("#")

            puuid = cachedPuuids.get(riotId)
            if puuid is None:
                url = f"{LOL_AMERICA_REGION_URL}/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
                response = requests.get(url, headers=riotApiHeaders, timeout=10)
                response.raise_for_status()
                puuid = response.json()["puuid"]
                if debugFlag:
                    LOG.debug(response.json())
                time.sleep(0.1)

            url = f"{LOL_NA1_PLATFORM_API_URL}/lol/league/v4/entries/by-puuid/{puuid}"
            response = requests.get(url, headers=riotApiHeaders, timeout=10)
            response.raise_for_status()
            obj = response.json()

            if debugFlag:
                LOG.debug(obj)
            newState[puuid] = {"riot_id": riotId}
            if obj.__len__() == 0:
                unrankedPlayers.append(gameName)
            else:
                friendsArr.append(rankedPlayer(puuid, gameName, obj[0]["tier"], obj[0]["rank"], obj[0]["leaguePoints"]))
                newState[puuid].update(tier=obj[0]["tier"], rank=obj[0]["rank"], lp=obj[0]["leaguePoints"])
            time.sleep(0.1)

        sortedPlayers = sorted(friendsArr)
        currTimestamp = getTimeStamp()

        lastSortedPlayers = rankedPlayersFromState(lastState)
        if debugFlag and len(sortedPlayers) > 0:
            sortedPlayers[0].playerLP += 1
            if len(sortedPlayers) > 1:
                sortedPlayers[-1].playerLP -= 1
            LOG.debug("--- Debug LP manipulation applied (top +1, bottom -1) ---")
        changed = hasDataChanged(sortedPlayers, lastSortedPlayers)

        if debugFlag:
            LOG.debug("--- New player data ---")
            for p in sortedPlayers:
                LOG.debug(f"  {p.playerName}: {p.playerTier} {p.playerRank} {p.playerLP} LP")
            LOG.debug("--- Old player data ---")
            for p in lastSortedPlayers:
                LOG.debug(f"  {p.playerName}: {p.playerTier} {p.playerRank} {p.playerLP} LP")
            LOG.debug(f"--- Changes detected: {changed} ---")
            LOG.debug("\n" + describeChanges(sortedPlayers, lastSortedPlayers))

            message = generateMessage(currTimestamp, sortedPlayers, unrankedPlayers, lastSortedPlayers)
            LOG.debug(f"--- Generated message ---\n{message}")
            messageHost(message)

        if not debugFlag and changed:
            message = generateMessage(currTimestamp, sortedPlayers, unrankedPlayers, lastSortedPlayers)
            response = messageRankedRaceChannel(message)
            storeState(newState)
            return 1

        # Nothing to post, but still save so new puuids and renames get cached
        if not debugFlag:
            storeState(newState)

        return -1

    except requests.exceptions.RequestException as e:
        LOG.error("Error: ", e, e.strerror)
        PageError(traceback.format_exc())
        return 0
