from requests import get

# Data Dragon
DATA_DRAGON_URL = "https://ddragon.leagueoflegends.com"
DATA_DRAGON_VERSIONS_URL = f"{DATA_DRAGON_URL}/api/versions.json"


def getVersionFile():
    response = get(DATA_DRAGON_VERSIONS_URL, timeout=10)

    response.raise_for_status()
    return response.json()
