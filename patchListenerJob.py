import requests
import os
import logging

from bs4 import BeautifulSoup
from data import NEWS_CHANNEL_ID

LAST_RUN_FILENAME = "./lastPatchVersion.txt"

class PatchNotPostedException(Exception):
    pass

def get_previous_patch():
    if os.path.exists(LAST_RUN_FILENAME):
        with open(LAST_RUN_FILENAME, "r") as lastVersioneFile:
            return lastVersioneFile.read()
    return "0"

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
    return f'https://www.leagueoflegends.com/en-us/news/game-updates/patch-{patch_version}-notes/'

def get_current_patch_image_uri(patch_version):
    r = requests.get(get_patch_notes_url(patch_version))
    if (r.status_code != 200):
        raise PatchNotPostedException
    soup = BeautifulSoup(r.content, "html.parser")
    links = soup.find_all("a", class_="skins cboxElement")
    for link in links:
        return link.get("href")

def check_for_patch(riot_api_key, discord_bot_api_key, debug=False):  
    LOG = logging.getLogger("patchListenerJob")

    previous_patch_id = get_previous_patch()
    LOG.info("Test log")
    guess_patch_id = guess_next_patch(previous_patch_id)
    LOG.debug(f"Patch guess: {guess_patch_id}")
    
    if debug:
        LOG.debug(f"Guess Patch: '{guess_patch_id}', Last Patch: '{previous_patch_id}, Equal? '{guess_patch_id == previous_patch_id}'")
    
    if previous_patch_id != guess_patch_id and not debug:
        patch_announcement_message = f"## Patch {guess_patch_id} just dropped!\n{get_patch_notes_url(guess_patch_id)}\n\n"
        patch_announcement_message += get_current_patch_image_uri(guess_patch_id)
        
        LOG.info(f"Posting message to discord {patch_announcement_message}")
        postReturn = requests.post(f"https://discord.com/api/v10/channels/{NEWS_CHANNEL_ID}/messages", 
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"content": patch_announcement_message, "tts": "false"})
        LOG.info(f"Call returned with code {postReturn.status_code}")
        store_previous_patch(guess_patch_id)
        if postReturn.status_code == 200:
           return 1
        else:
            return 0
    
    return -1
