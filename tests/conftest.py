import json
import logging
import os
import sys
import time

import pytest
import requests

# config/__init__.py reads these at import time. Set fake values first so tests never
# need (or touch) a real config/.env. load_dotenv won't override variables already set.
for name in (
    "RIOT_API_KEY",
    "DISCORD_BOT_TOKEN",
    "DISCORD_CHANNEL_ID",
    "NEWS_CHANNEL_ID",
    "HOST_USER_ID",
    "PERSONAL_EMAIL",
    "PROJECT_EMAIL",
    "PROJECT_EMAIL_APP_PASSWORD",
):
    os.environ[name] = f"test-{name.lower()}"

import emailPage  # noqa: E402
import runner  # noqa: E402
from clients import discord_http_client, riot_developer_api_client  # noqa: E402
from config import DISCORD_CHANNEL_ID, NEWS_CHANNEL_ID, runtime  # noqa: E402
from patchListenerJob import getPatchNotesUrl  # noqa: E402
from riotApiConstants import DATA_DRAGON_VERSIONS_URL  # noqa: E402

# Fake players tracked in config/players.toml
RIOT_IDS = ["SHEEP#NA1", "COW#NA1", "WINNER#GAMER", "KOALA#NA1"]

# What the fake Riot API returns for each player. An empty list means unranked.
RANKED = {
    "SHEEP#NA1": [{"tier": "GOLD", "rank": "II", "leaguePoints": 40}],
    "COW#NA1": [{"tier": "SILVER", "rank": "IV", "leaguePoints": 10}],
    "WINNER#GAMER": [{"tier": "DIAMOND", "rank": "I", "leaguePoints": 75}],
    "KOALA#NA1": [],
}

# Latest version on Data Dragon (game version 15.22 is patch 25.22)
VERSIONS = ["15.22.1", "15.21.1"]

PATCH_IMAGE = "https://fake.cdn/patch-25-22-highlights.jpg"
PATCH_TAGLINE = "Sheep rise, cows fall."
PATCH_PAGE = f"""
<html>
  <head><meta property="og:description" content="{PATCH_TAGLINE}"></head>
  <body><a class="skins cboxElement" href="{PATCH_IMAGE}">Patch highlights</a></body>
</html>
""".encode()


def puuidFor(riotId):
    return "puuid-" + riotId.replace("#", "-").lower()


def stateEntry(riotId, tier=None, rank=None, lp=None):
    entry = {"riot_id": riotId}
    if tier is not None:
        entry.update(tier=tier, rank=rank, lp=lp)
    return {puuidFor(riotId): entry}


class FakeResponse:
    def __init__(self, jsonData=None, statusCode=200, content=b""):
        self._jsonData = jsonData
        self.status_code = statusCode
        self.content = content

    def json(self):
        return self._jsonData

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error")


def respond(value):
    """Turn a fake data value into a response: an exception is raised, an int is an error status."""
    if isinstance(value, Exception):
        raise value
    if isinstance(value, int):
        return FakeResponse(statusCode=value)
    return FakeResponse(value)


class FakeInternet:
    """Stands in for Riot, Data Dragon, the patch notes site, Discord, and Gmail.

    Tests change the data on it to set up a scenario, then check what was sent.
    Any request it doesn't recognise fails the test, so nothing reaches the real network.
    """

    def __init__(self):
        self.ranked = {puuidFor(riotId): entries for riotId, entries in RANKED.items()}
        self.versions = VERSIONS
        self.patchPages = {"25-22": PATCH_PAGE}
        self.requests = []
        self.emails = []

    def get(self, url, **kwargs):
        self.requests.append(("GET", url, None))
        if "/riot/account/v1/accounts/by-riot-id/" in url:
            gameName, tagLine = url.split("/")[-2:]
            return FakeResponse({"puuid": puuidFor(f"{gameName}#{tagLine}")})
        if "/lol/league/v4/entries/by-puuid/" in url:
            return respond(self.ranked[url.split("/")[-1]])
        if url == DATA_DRAGON_VERSIONS_URL:
            return respond(self.versions)
        if "/news/game-updates/" in url:
            for patch, page in self.patchPages.items():
                if url == getPatchNotesUrl(patch):
                    return FakeResponse(content=page)
            return FakeResponse(statusCode=404)
        raise AssertionError(f"Unexpected GET {url}")

    def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs.get("json")))
        if url.endswith("/users/@me/channels"):
            return FakeResponse({"id": "dm-channel"})
        if url.endswith("/messages"):
            return FakeResponse({"id": "message"})
        raise AssertionError(f"Unexpected POST {url}")

    def postsTo(self, channelId):
        return [body for method, url, body in self.requests if method == "POST" and f"/channels/{channelId}/" in url]

    @property
    def rankedPosts(self):
        return self.postsTo(DISCORD_CHANNEL_ID)

    @property
    def newsPosts(self):
        return self.postsTo(NEWS_CHANNEL_ID)

    @property
    def hostDms(self):
        return self.postsTo("dm-channel")

    @property
    def accountLookups(self):
        return [url for method, url, _ in self.requests if "/riot/account/" in url]


@pytest.fixture(autouse=True)
def resetRuntime():
    runtime.DEBUG = False
    yield
    runtime.DEBUG = False


@pytest.fixture
def internet(monkeypatch):
    fake = FakeInternet()

    class FakeSmtp:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, user, password):
            pass

        def send_message(self, message):
            fake.emails.append(message)

    monkeypatch.setattr(requests, "get", fake.get)
    monkeypatch.setattr(requests, "post", fake.post)
    monkeypatch.setattr(riot_developer_api_client, "get", fake.get)
    monkeypatch.setattr(discord_http_client, "post", fake.post)
    monkeypatch.setattr(emailPage.smtplib, "SMTP_SSL", FakeSmtp)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    return fake


class Project:
    """A throwaway copy of the folders the jobs read and write, with the fake players configured."""

    def __init__(self, root):
        self.root = root
        self.playersFile = root / "config" / "players.toml"
        self.stateFile = root / "data" / "state" / "state.json"
        self.patchFile = root / "data" / "state" / "lastPatchVersion.txt"
        self.playersFile.parent.mkdir(parents=True)
        self.stateFile.parent.mkdir(parents=True)
        (root / "data" / "logs").mkdir(parents=True)
        self.setPlayers(RIOT_IDS)

    def setPlayers(self, riotIds):
        self.playersFile.write_text("".join(f'[[player]]\nriot_id = "{riotId}"\n\n' for riotId in riotIds))

    def setState(self, state):
        self.stateFile.write_text(json.dumps(state))

    def readState(self):
        return json.loads(self.stateFile.read_text())


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # runner.main() points logging at data/logs; keep it from opening a log file per test
    monkeypatch.setattr(logging, "basicConfig", lambda **_: None)
    return Project(tmp_path)


@pytest.fixture
def runJobs(project, internet, monkeypatch):
    """Runs runner.main() the way the scheduled job does, optionally in debug mode."""

    def run(debug=False):
        monkeypatch.setattr(sys, "argv", ["runner.py", "debug"] if debug else ["runner.py"])
        runner.main()

    return run
