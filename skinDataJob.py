import json
import logging
import os
import pickle
import pprint
import requests

from riotApiConstants import DATA_DRAGON_URL, DATA_DRAGON_VERSIONS_URL

LAST_PROCESSED_PATCH_FILE = "lastProcessedPatch.pkl"
PROCESSED_PATCH_FILE = "./data/lastProcessedPatch.json"

def storeData(last_processed_patch):
    with open(LAST_PROCESSED_PATCH_FILE, "wb") as lastMessageFile:
        pickle.dump(last_processed_patch, lastMessageFile)

def loadData():
    db = ""
    if os.path.exists(LAST_PROCESSED_PATCH_FILE):
        with open(LAST_PROCESSED_PATCH_FILE, "rb") as lastMessageFile:
            db = pickle.load(lastMessageFile)
    
    return db

def getMostRecentDataDragonVersion():
    dd_response = requests.get(DATA_DRAGON_VERSIONS_URL)
    dd_response.raise_for_status()
    patch_version = dd_response.json()[0]
    return patch_version
    
def getMostRecentProcessedPatch():
    return loadData()

def getChampionsList(patch_number):
    dd_response = requests.get(f"{DATA_DRAGON_URL}/cdn/{patch_number}/data/en_US/champion.json")
    dd_response.raise_for_status()
    return list(dict(dd_response.json()["data"]).keys())

def extractSkinLine(skin_name, champion_name):
    return skin_name.replace(champion_name, "").replace("Prestige", "").strip()

def generateSplashArtLink(artType, champion_id, skin_num):
    return f"{DATA_DRAGON_URL}/cdn/img/champion/{artType}/{champion_id}_{skin_num}.jpg"
 
def addSkinlineDataFor(patch_number, champion_id, skinline_dict):
    dd_response = requests.get(f"{DATA_DRAGON_URL}/cdn/{patch_number}/data/en_US/champion/{champion_id}.json")
    dd_response.raise_for_status()
    skin_dict = dict(dd_response.json()["data"][champion_id])
    for skin_obj in skin_dict["skins"]:
        if (skin_obj["name"] != "default" and "Prestige" not in skin_obj["name"]):
            skinline = extractSkinLine(skin_obj['name'], skin_dict['name'])
            skin_link_obj = [skin_obj['name'], generateSplashArtLink("splash", champion_id, skin_obj["num"])]
            if skinline not in skinline_dict:
                skinline_dict[skinline] = [skin_link_obj]
            else:
                skinline_dict[skinline].append(skin_link_obj)

def filterForFiveStack(skinline_dict):
    filtered_skinline_dict = dict()
    for key, value in skinline_dict.items():
        if len(value) >= 5:
            filtered_skinline_dict[key] = value
            
    return filtered_skinline_dict

def writeOutSkinlineData(skinline_dict):
    with open(PROCESSED_PATCH_FILE, "w") as f:
        json.dump(skinline_dict, f)
    

def skinLineDataJob():
    LOG = logging.getLogger("skinLineDataJob")
    most_recent_data_dragon_version = getMostRecentDataDragonVersion()
    if most_recent_data_dragon_version <= getMostRecentProcessedPatch():
        LOG.debug(f"Patch {most_recent_data_dragon_version} already processed.")
        return -1
    
    champion_names = getChampionsList(most_recent_data_dragon_version)
    
    skinline_dict = dict()
    LOG.debug(f"Processing for Patch {most_recent_data_dragon_version} - Started")
    for champion_id in champion_names:
        addSkinlineDataFor(most_recent_data_dragon_version, champion_id, skinline_dict)
    LOG.debug(f"Processing for Patch {most_recent_data_dragon_version} - Complete")
    LOG.debug(f"Filtering for Patch {most_recent_data_dragon_version} - Started")
    filtered_skinline_dict = filterForFiveStack(skinline_dict)
    filtered_skinline_dict = dict(sorted(filtered_skinline_dict.items()))
    LOG.debug(f"Filtering for Patch {most_recent_data_dragon_version} - Complete")
    
    # Wrap up
    storeData(most_recent_data_dragon_version)
    writeOutSkinlineData(filtered_skinline_dict)
    return 1    
    
if __name__ == "__main__":
    skinLineDataJob()