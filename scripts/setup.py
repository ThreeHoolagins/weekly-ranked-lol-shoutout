"""Interactive helper to set up everything the bot needs to run.

1. Installs the Python packages in requirements.txt with pip.
2. config/.env: walks through every variable config/__init__.py reads, shows what's already
   set, and validates input against known formats before saving.
3. config/players.toml: lists the tracked players and lets you add or remove them.
4. Creates the data/state/ and data/logs/ folders the jobs write into.

Usage (works from any directory, just point at the file):
    python scripts/setup.py
"""

import sys

if sys.version_info < (3, 11):
    sys.exit("This project needs Python 3.11 or newer (it uses tomllib).")

import getpass
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
REQUIREMENTS_PATH = SCRIPTS_DIR / "requirements.txt"
ENV_PATH = PROJECT_ROOT / "config" / ".env"
PLAYERS_PATH = PROJECT_ROOT / "config" / "players.toml"
REQUIRED_DIRS = ["data/state", "data/logs"]

SNOWFLAKE = r"\d{17,20}"
EMAIL = r"[^@\s]+@[^@\s]+\.[^@\s]+"
# Riot ID is GameName#Tag: name is 3-16 characters, tag is 3-5 letters/digits
RIOT_ID = r"[^#]{3,16}#[^\W_]{3,5}"

# (name, description, regex or None, is_secret)  # noqa: ERA001
VARIABLES = [
    (
        "RIOT_API_KEY",
        "Riot API key from https://developer.riotgames.com",
        r"RGAPI-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        True,
    ),
    (
        "DISCORD_BOT_TOKEN",
        'Discord bot token, without the "Bot " prefix',
        r"[\w-]{24,}\.[\w-]{6,}\.[\w-]{27,}",
        True,
    ),
    (
        "DISCORD_CHANNEL_ID",
        "Channel ID to post the ranked summary in",
        SNOWFLAKE,
        False,
    ),
    (
        "NEWS_CHANNEL_ID",
        "Channel ID to post patch notes in",
        SNOWFLAKE,
        False,
    ),
    (
        "HOST_USER_ID",
        "Discord user ID that receives debug DMs",
        SNOWFLAKE,
        False,
    ),
    (
        "PERSONAL_EMAIL",
        "Email address to send to",
        EMAIL,
        False,
    ),
    (
        "PROJECT_EMAIL",
        "Gmail address to send from",
        EMAIL,
        False,
    ),
    (
        "PROJECT_EMAIL_APP_PASSWORD",
        "Gmail app password (16 letters, spaces optional)",
        r"[a-zA-Z]{4} ?[a-zA-Z]{4} ?[a-zA-Z]{4} ?[a-zA-Z]{4}",
        True,
    ),
]


def parseEnv(path):
    """Read KEY=VALUE pairs from a .env file, stripping surrounding quotes."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            quoteChar, value = value[0], value[1:-1]
            if quoteChar == '"':
                value = value.replace('\\"', '"').replace("\\\\", "\\")
        values[key] = value
    return values


def isValid(value, pattern):
    if not value:
        return False
    return pattern is None or re.fullmatch(pattern, value) is not None


def mask(value):
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def askYesNo(prompt, default=True):
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer y or n.")


def normalize(name, value):
    value = value.strip()
    if name == "DISCORD_BOT_TOKEN" and value.lower().startswith("bot "):
        value = value[4:].strip()
    return value


def promptValue(name, description, pattern, secret):
    # getpass reads the console directly, so only use it in an interactive terminal
    hide = secret and sys.stdin.isatty()
    reader = getpass.getpass if hide else input
    hint = " (input hidden)" if hide else ""
    while True:
        value = normalize(name, reader(f"  Enter {name}{hint}: "))
        if isValid(value, pattern):
            return value
        if not value:
            print("  A value is required.")
        else:
            print(f"  That doesn't look right. Expected: {description}")


def collect(existing):
    result = {}
    for index, (name, description, pattern, secret) in enumerate(VARIABLES, 1):
        print(f"\n[{index}/{len(VARIABLES)}] {name}")
        print(f"  {description}")
        current = existing.get(name, "")
        if current:
            shown = mask(current) if secret else current
            if isValid(current, pattern):
                print(f"  Current value: {shown}")
                if askYesNo("  Keep it?"):
                    result[name] = current
                    continue
            else:
                print(f"  Current value {shown} doesn't match the expected format.")
                if not askYesNo("  Replace it?"):
                    result[name] = current
                    continue
        else:
            print("  Not set.")
        result[name] = promptValue(name, description, pattern, secret)
    return result


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def writeEnv(values, extras):
    lines = ["# Generated by scripts/setup.py. Values with spaces need quotes.", ""]
    for name, description, _, _ in VARIABLES:
        lines.append(f"# {description}")
        lines.append(f"{name}={quote(values[name])}")
        lines.append("")
    if extras:
        lines.append("# Other values carried over from the previous .env")
        for name, value in extras.items():
            lines.append(f"{name}={quote(value)}")
        lines.append("")
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def backup(path):
    if path.exists():
        backupPath = path.with_name(path.name + ".bak")
        shutil.copy2(path, backupPath)
        print(f"Backed up existing {path.name} to {backupPath.name}")


def heading(title):
    print(f"\n{'=' * 50}\n{title}\n{'=' * 50}")


def setupPackages():
    heading("Step 1: Python packages")
    print(f"Python: {sys.executable}")
    if sys.prefix == sys.base_prefix:
        print("Note: no virtual environment is active, packages will install globally.")
    if not REQUIREMENTS_PATH.exists():
        print(f"{REQUIREMENTS_PATH} not found, skipping.")
        return
    if not askYesNo(f"Install packages from {REQUIREMENTS_PATH.name} with pip?"):
        print("Skipped package install.")
        return

    # Use this interpreter's pip so packages land where the bot will run from
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])
    if result.returncode == 0:
        print("Packages installed.")
    else:
        print(f"pip exited with code {result.returncode}. Fix the error above and rerun, or install manually with:")
        print(f'  "{sys.executable}" -m pip install -r "{REQUIREMENTS_PATH}"')
        if not askYesNo("Continue with the rest of setup?"):
            raise SystemExit(1)


def setupEnv():
    heading("Step 2: config/.env")
    print(f"Target: {ENV_PATH}")

    existing = parseEnv(ENV_PATH)
    if ENV_PATH.exists():
        valid = sum(1 for name, _, pattern, _ in VARIABLES if isValid(existing.get(name, ""), pattern))
        print(f"Found existing .env with {valid}/{len(VARIABLES)} required values set and valid.")
        if valid == len(VARIABLES) and not askYesNo("Everything looks good. Review the values anyway?", default=False):
            return
    else:
        print("No .env found, a new one will be created.")

    values = collect(existing)

    knownNames = {name for name, *_ in VARIABLES}
    extras = {k: v for k, v in existing.items() if k not in knownNames}

    print("\nSummary:")
    for name, _, _, secret in VARIABLES:
        print(f"  {name} = {mask(values[name]) if secret else values[name]}")
    if extras:
        print(f"  (+{len(extras)} other value(s) kept: {', '.join(extras)})")

    if not askYesNo(f"\nWrite these to {ENV_PATH.name}?"):
        print(f"Skipped, {ENV_PATH.name} not written.")
        return

    backup(ENV_PATH)
    writeEnv(values, extras)
    print(f"Wrote {ENV_PATH}")


def loadPlayers():
    if not PLAYERS_PATH.exists():
        return []
    try:
        with open(PLAYERS_PATH, "rb") as playersFile:
            return tomllib.load(playersFile).get("player", [])
    except tomllib.TOMLDecodeError as error:
        print(f"Couldn't read {PLAYERS_PATH.name}: {error}")
        if askYesNo("Start from an empty player list instead?"):
            return []
        raise SystemExit(f"Fix {PLAYERS_PATH.name} by hand and rerun setup.") from error


def describePlayer(player):
    discordId = player.get("discord_id")
    return player["riot_id"] + (f" (Discord {discordId})" if discordId else "")


def printPlayers(players):
    if not players:
        print("  No players yet.")
    for index, player in enumerate(players, 1):
        print(f"  {index}. {describePlayer(player)}")


def promptPlayer(players):
    taken = {p["riot_id"].lower() for p in players}
    while True:
        riotId = input("  Riot ID (Name#Tag, blank to cancel): ").strip()
        if not riotId:
            return None
        if not re.fullmatch(RIOT_ID, riotId):
            print(
                "  That doesn't look right. Expected Name#Tag, e.g. Faker#KR1 "
                "(name 3-16 characters, tag 3-5 letters/digits)."
            )
            continue
        if riotId.lower() in taken:
            print(f"  {riotId} is already in the list.")
            continue
        break

    player = {"riot_id": riotId}
    while True:
        discordId = input("  Discord user ID (optional, blank to skip): ").strip()
        if not discordId:
            break
        if re.fullmatch(SNOWFLAKE, discordId):
            player["discord_id"] = discordId
            break
        print("  Discord IDs are 17-20 digits (right click the user > Copy User ID with developer mode on).")
    return player


def promptRemoval(players):
    while True:
        choice = input(f"  Number to remove (1-{len(players)}, blank to cancel): ").strip()
        if not choice:
            return
        if choice.isdigit() and 1 <= int(choice) <= len(players):
            removed = players.pop(int(choice) - 1)
            print(f"  Removed {removed['riot_id']}.")
            return
        print("  Not a valid number.")


def writePlayers(players):
    lines = [
        "# Generated by scripts/setup.py. One [[player]] block per person.",
        "# riotId is the in-game Name#Tag. discordId is optional.",
    ]
    for player in players:
        lines.append("")
        lines.append("[[player]]")
        lines.append(f"riot_id = {quote(player['riot_id'])}")
        if player.get("discord_id"):
            lines.append(f"discord_id = {quote(player['discord_id'])}")
    PLAYERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAYERS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def setupPlayers():
    heading("Step 3: config/players.toml")
    print(f"Target: {PLAYERS_PATH}")

    original = loadPlayers()
    players = [dict(p) for p in original]
    if not PLAYERS_PATH.exists():
        print("No config/players.toml found, a new one will be created.")

    while True:
        print(f"\nTracked players ({len(players)}):")
        printPlayers(players)
        choice = input("\n[a]dd, [r]emove, or [d]one? ").strip().lower()
        if choice in ("a", "add"):
            player = promptPlayer(players)
            if player:
                players.append(player)
                print(f"  Added {describePlayer(player)}.")
        elif choice in ("r", "remove"):
            if players:
                promptRemoval(players)
            else:
                print("  Nothing to remove.")
        elif choice in ("d", "done", ""):
            if not players and not askYesNo(
                "  No players added, the ranked job needs at least one. Finish anyway?", default=False
            ):
                continue
            break
        else:
            print("  Please answer a, r, or d.")

    if players == original and PLAYERS_PATH.exists():
        print("No changes to config/players.toml.")
        return
    if not askYesNo(f"\nWrite {len(players)} player(s) to {PLAYERS_PATH.name}?"):
        print(f"Skipped, {PLAYERS_PATH.name} not written.")
        return

    backup(PLAYERS_PATH)
    writePlayers(players)
    print(f"Wrote {PLAYERS_PATH}")


def setupDirs():
    heading("Step 4: folders")
    for name in REQUIRED_DIRS:
        path = PROJECT_ROOT / name
        if path.is_dir():
            print(f"  {name}/ already exists.")
        else:
            path.mkdir(parents=True)
            print(f"  Created {name}/")


def main():
    print("weekly-ranked-lol-shoutout setup")
    print("Press Ctrl+C at any time to quit. Each step asks before writing.")
    setupPackages()
    setupEnv()
    setupPlayers()
    setupDirs()
    print("\nSetup complete.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Anything not yet written was discarded.")
        sys.exit(1)
