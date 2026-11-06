import tomllib

import pytest
from dotenv import dotenv_values

import scripts.setup

ENV_VALUES = {
    "RIOT_API_KEY": "RGAPI-0123abcd-4567-89ab-cdef-0123456789ab",
    "DISCORD_BOT_TOKEN": "SHEEPsheepSHEEPsheepSHEEP.COWcow.WINNERwinnerWINNERwinnerWINNER",
    "DISCORD_CHANNEL_ID": "111111111111111111",
    "NEWS_CHANNEL_ID": "222222222222222222",
    "HOST_USER_ID": "333333333333333333",
    "PERSONAL_EMAIL": "sheep@farm.example",
    "PROJECT_EMAIL": "cow@farm.example",
    "PROJECT_EMAIL_APP_PASSWORD": "baaa baaa mooo mooo",
}


@pytest.fixture
def answers(monkeypatch, tmp_path):
    """Points setup at a temp folder and feeds it the given answers in order."""
    monkeypatch.setattr(scripts.setup, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(scripts.setup, "PLAYERS_PATH", tmp_path / "players.toml")

    def feed(*replies):
        remaining = iter(replies)

        def reply(prompt=""):
            return next(remaining)

        monkeypatch.setattr("builtins.input", reply)
        monkeypatch.setattr(scripts.setup.getpass, "getpass", reply)

    return feed


def test_setupEnvWritesEveryValue(answers):
    # Pasting the token with its "Bot " prefix should still save just the token
    replies = [f"Bot {value}" if name == "DISCORD_BOT_TOKEN" else value for name, value in ENV_VALUES.items()]
    answers(*replies, "y")

    scripts.setup.setupEnv()

    assert dotenv_values(scripts.setup.ENV_PATH) == ENV_VALUES


def test_setupPlayersWritesEveryPlayer(answers):
    answers(
        *("a", "SHEEP#NA1", "123456789012345678"),
        *("a", "COW#NA1", ""),
        *("a", "WINNER#GAMER", ""),
        "d",
        "y",
    )

    scripts.setup.setupPlayers()

    with open(scripts.setup.PLAYERS_PATH, "rb") as playersFile:
        assert tomllib.load(playersFile)["player"] == [
            {"riot_id": "SHEEP#NA1", "discord_id": "123456789012345678"},
            {"riot_id": "COW#NA1"},
            {"riot_id": "WINNER#GAMER"},
        ]
