import requests
import os

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

def get_current_patch_image_uri(patch_version):
    r = requests.get(f'https://www.leagueoflegends.com/en-us/news/game-updates/patch-{patch_version}-notes/')
    soup = BeautifulSoup(r.content, "html.parser")
    links = soup.find_all("a", class_="skins cboxElement")
    for link in links:
        print(link.get("href"))
        return link.get("href")

def check_for_patch(riot_api_key, discord_bot_api_key, debug=False):    
    previous_patch_id = get_previous_patch()
    current_patch_id = get_current_patch(riot_api_key)
    
    if debug:
        print(f"Current Patch: '{current_patch_id}', Last Patch: '{previous_patch_id}, Equal? '{current_patch_id == previous_patch_id}'")
    
    if previous_patch_id != current_patch_id and not debug:
        patch_diagram_url = get_current_patch_image_uri(current_patch_id)
        
        postReturn = requests.post(f"https://discord.com/api/v10/channels/{NEWS_CHANNEL_ID}/messages", 
            headers={"Authorization": f"{discord_bot_api_key}"},
            json={"content": patch_diagram_url, "tts": "false"})
        store_previous_patch(current_patch_id)
        if postReturn.status_code == 200:
           return 1
    
    return -1
