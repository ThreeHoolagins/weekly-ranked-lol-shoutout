import requests
import os
import logging

from bs4 import BeautifulSoup
from data import NEWS_CHANNEL_ID

DATA_DRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
LAST_RUN_FILENAME = "./lastPatchVersion.txt"

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
        

def get_current_patch(riot_api_key):
    riot_api_headers = {
        "X-Riot-Token": riot_api_key,
        "Accept-Language" : "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }

    patch_list = requests.get(DATA_DRAGON_VERSIONS_URL, headers=riot_api_headers).json()
    return get_readable_patch(patch_list[0])
    
def get_readable_patch(patch_id):
    patch_id_split = patch_id.split(".")
    if (patch_id_split[0] == "15"):
        return f"25-{patch_id_split[1]}"
    
    return patch_id

def get_patch_notes_url(patch_version):
    return f'https://www.leagueoflegends.com/en-us/news/game-updates/patch-{patch_version}-notes/'

def get_current_patch_image_uri(patch_version):
    r = requests.get(get_patch_notes_url(patch_version))
    soup = BeautifulSoup(r.content, "html.parser")
    links = soup.find_all("a", class_="skins cboxElement")
    for link in links:
        return link.get("href")

def check_for_patch(riot_api_key, discord_bot_api_key, debug=False):  
    LOG = logging.getLogger("patchListenerJob")

    previous_patch_id = get_previous_patch()
    current_patch_id = get_current_patch(riot_api_key)
    
    if debug:
        LOG.debug(f"Current Patch: '{current_patch_id}', Last Patch: '{previous_patch_id}, Equal? '{current_patch_id == previous_patch_id}'")
    
    if previous_patch_id != current_patch_id and not debug:
        patch_announcement_message = f"## Patch {current_patch_id} just dropped!\n{get_patch_notes_url(current_patch_id)}\n\n"
        patch_announcement_message += get_current_patch_image_uri(current_patch_id)
        
        LOG.info(f"Posting message to discord {patch_announcement_message}")
        postReturn = requests.post(f"https://discord.com/api/v10/channels/{NEWS_CHANNEL_ID}/messages", 
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"content": patch_announcement_message, "tts": "false"})
        LOG.info(f"Call returned with code {postReturn.status_code}")
        store_previous_patch(current_patch_id)
        if postReturn.status_code == 200:
           return 1
        else:
            return 0
    
    return -1
