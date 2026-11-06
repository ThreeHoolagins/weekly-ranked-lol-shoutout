import logging
import os

import requests
from bs4 import BeautifulSoup

from clients.discord_http_client import messageHost, messageNewsChannel

LAST_RUN_FILENAME = "./data/state/lastPatchVersion.txt"
# League gold
PATCH_ACCENT_COLOR = 0xC89B3C

# Discord message component values
IS_COMPONENTS_V2 = 1 << 15
COMPONENT_BUTTON = 2
COMPONENT_SECTION = 9
COMPONENT_TEXT = 10
COMPONENT_MEDIA_GALLERY = 12
COMPONENT_CONTAINER = 17
BUTTON_STYLE_LINK = 5


class PatchNotPostedException(Exception):
    pass


def getPreviousPatch():
    if os.path.exists(LAST_RUN_FILENAME):
        with open(LAST_RUN_FILENAME) as lastVersioneFile:
            return lastVersioneFile.read()
    return longFetchPatch()


def longFetchPatch():
    r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10)
    patchParts = r.json()[0].split(".")
    return f"{int(patchParts[0]) + 10}-{int(patchParts[1]) - 1}"


def storePreviousPatch(currentPatch):
    with open(LAST_RUN_FILENAME, "w") as lastVersioneFile:
        lastVersioneFile.write(currentPatch)


def guessNextPatch(lastPatch):
    patchParts = lastPatch.split("-")
    patchParts[1] = str(int(patchParts[1]) + 1)

    if int(patchParts[1]) > 24:
        patchParts[0] = str(int(patchParts[0]) + 1)
        patchParts[1] = "1"

    return "-".join(patchParts)


def getPatchNotesUrl(patchVersion):
    return f"https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-{patchVersion}-notes/"


# Scrapes the patch notes page for the highlights image and Riot's tagline
def getPatchDetails(patchVersion):
    r = requests.get(getPatchNotesUrl(patchVersion), timeout=10)
    if r.status_code != 200:
        raise PatchNotPostedException
    soup = BeautifulSoup(r.content, "html.parser")
    highlights = soup.find("a", class_="skins cboxElement")
    tagline = soup.find("meta", property="og:description")
    return (highlights.get("href") if highlights else None, tagline.get("content") if tagline else None)


# Uses Discord's Components V2 layout so the button can sit inside the box.
# V2 messages can't have content or embeds, everything goes in components.
def buildPatchAnnouncement(patchVersion):
    imageUri, tagline = getPatchDetails(patchVersion)
    text = f"## \u2694\ufe0f Patch {patchVersion.replace('-', '.')} has landed"
    if tagline:
        text += f"\n{tagline}"
    box = [
        {
            "type": COMPONENT_SECTION,
            "components": [{"type": COMPONENT_TEXT, "content": text}],
            "accessory": {
                "type": COMPONENT_BUTTON,
                "style": BUTTON_STYLE_LINK,
                "label": "Read Patch Notes",
                "emoji": {"name": "\U0001f4dc"},
                "url": getPatchNotesUrl(patchVersion),
            },
        }
    ]
    if imageUri:
        box.append({"type": COMPONENT_MEDIA_GALLERY, "items": [{"media": {"url": imageUri}}]})
    return {
        "flags": IS_COMPONENTS_V2,
        "components": [{"type": COMPONENT_CONTAINER, "accent_color": PATCH_ACCENT_COLOR, "components": box}],
    }


def checkForPatch(riotApiKey, discordBotApiKey, debug=False):
    LOG = logging.getLogger("patchListenerJob")

    previousPatchId = getPreviousPatch()
    LOG.info(f"Previous Patch: {previousPatchId}")
    guessPatchId = guessNextPatch(previousPatchId)
    LOG.info(f"Patch guess: {guessPatchId}")

    if debug:
        LOG.debug(
            f"Guess Patch: '{guessPatchId}', Last Patch: '{previousPatchId}, Equal? '{guessPatchId == previousPatchId}'"
        )
        # Preview the next patch if it's out, otherwise the last one posted
        try:
            announcement = buildPatchAnnouncement(guessPatchId)
        except PatchNotPostedException:
            announcement = buildPatchAnnouncement(previousPatchId)
        LOG.debug(f"--- Generated patch announcement ---\n{announcement}")
        messageHost(announcement)
        return -1

    if previousPatchId != guessPatchId:
        announcement = buildPatchAnnouncement(guessPatchId)
        messageNewsChannel(announcement)
        storePreviousPatch(guessPatchId)

    return -1
