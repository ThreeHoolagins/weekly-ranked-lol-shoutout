import requests
import os
import logging

from bs4 import BeautifulSoup
from config import NEWS_CHANNEL_ID
from discordApiConstants import DISCORD_API_URL
from messageGroup import dmHost

LAST_RUN_FILENAME = "./lastPatchVersion.txt"
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

def get_previous_patch():
    if os.path.exists(LAST_RUN_FILENAME):
        with open(LAST_RUN_FILENAME, "r") as lastVersioneFile:
            return lastVersioneFile.read()
    return long_fetch_patch()

def long_fetch_patch():
    r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
    patchParts = r.json()[0].split(".")
    return f"{int(patchParts[0])+10}-{int(patchParts[1])-1}"

def store_previous_patch(current_patch):
    if not os.path.exists(LAST_RUN_FILENAME):
        open(LAST_RUN_FILENAME, "x")
    with open(LAST_RUN_FILENAME, "w") as lastVersioneFile:
        lastVersioneFile.write(current_patch)

def guess_next_patch(last_patch):
    patch_parts = last_patch.split("-")
    patch_parts[1] = str(int(patch_parts[1]) + 1)

    if int(patch_parts[1]) > 24:
        patch_parts[0] = str(int(patch_parts[0])+1)
        patch_parts[1] = "1"
    
    return "-".join(patch_parts)

def get_patch_notes_url(patch_version):
    return f'https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-{patch_version}-notes/'

# Scrapes the patch notes page for the highlights image and Riot's tagline
def get_patch_details(patch_version):
    r = requests.get(get_patch_notes_url(patch_version))
    if (r.status_code != 200):
        raise PatchNotPostedException
    soup = BeautifulSoup(r.content, "html.parser")
    highlights = soup.find("a", class_="skins cboxElement")
    tagline = soup.find("meta", property="og:description")
    return (highlights.get("href") if highlights else None,
            tagline.get("content") if tagline else None)

# Uses Discord's Components V2 layout so the button can sit inside the box.
# V2 messages can't have content or embeds, everything goes in components.
def build_patch_announcement(patch_version):
    image_uri, tagline = get_patch_details(patch_version)
    text = f"## \u2694\ufe0f Patch {patch_version.replace('-', '.')} has landed"
    if tagline:
        text += f"\n{tagline}"
    box = [{
        "type": COMPONENT_SECTION,
        "components": [{"type": COMPONENT_TEXT, "content": text}],
        "accessory": {"type": COMPONENT_BUTTON, "style": BUTTON_STYLE_LINK, "label": "Read Patch Notes",
                      "emoji": {"name": "\U0001f4dc"}, "url": get_patch_notes_url(patch_version)},
    }]
    if image_uri:
        box.append({"type": COMPONENT_MEDIA_GALLERY, "items": [{"media": {"url": image_uri}}]})
    return {
        "flags": IS_COMPONENTS_V2,
        "components": [{"type": COMPONENT_CONTAINER, "accent_color": PATCH_ACCENT_COLOR, "components": box}],
    }

def check_for_patch(riot_api_key, discord_bot_api_key, debug=False):
    LOG = logging.getLogger("patchListenerJob")

    previous_patch_id = get_previous_patch()
    LOG.info(f"Previous Patch: {previous_patch_id}")
    guess_patch_id = guess_next_patch(previous_patch_id)
    LOG.info(f"Patch guess: {guess_patch_id}")

    if debug:
        LOG.debug(f"Guess Patch: '{guess_patch_id}', Last Patch: '{previous_patch_id}, Equal? '{guess_patch_id == previous_patch_id}'")
        # Preview the next patch if it's out, otherwise the last one posted
        try:
            announcement = build_patch_announcement(guess_patch_id)
        except PatchNotPostedException:
            announcement = build_patch_announcement(previous_patch_id)
        LOG.debug(f"--- Generated patch announcement ---\n{announcement}")
        dmHost(discord_bot_api_key, announcement)
        return -1

    if previous_patch_id != guess_patch_id:
        announcement = build_patch_announcement(guess_patch_id)

        LOG.info(f"Posting message to discord {announcement}")
        postReturn = requests.post(f"{DISCORD_API_URL}/v10/channels/{NEWS_CHANNEL_ID}/messages",
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"tts": False, **announcement})
        LOG.info(f"Call returned with code {postReturn.status_code}")
        store_previous_patch(guess_patch_id)
        if postReturn.status_code == 200:
           return 1
        else:
            return 0
    
    return -1
