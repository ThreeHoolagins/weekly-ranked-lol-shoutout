"""Interactive helper to set up everything the bot needs to run.

1. Installs the Python packages in requirements.txt with pip.
2. .env: walks through every variable config.py reads, shows what's already
   set, and validates input against known formats before saving.
3. players.toml: lists the tracked players and lets you add or remove them.
4. Creates the data/ and logs/ folders the jobs write into.

Usage (from anywhere):
    python setup.py
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
ENV_PATH = PROJECT_ROOT / ".env"
PLAYERS_PATH = PROJECT_ROOT / "players.toml"
REQUIRED_DIRS = ["data", "logs"]

SNOWFLAKE = r"\d{17,20}"
EMAIL = r"[^@\s]+@[^@\s]+\.[^@\s]+"
# Riot ID is GameName#Tag: name is 3-16 characters, tag is 3-5 letters/digits
RIOT_ID = r"[^#]{3,16}#[^\W_]{3,5}"

# (name, description, regex or None, is_secret)
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


def parse_env(path):
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
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            quote_char, value = value[0], value[1:-1]
            if quote_char == '"':
                value = value.replace('\\"', '"').replace("\\\\", "\\")
        values[key] = value
    return values


def is_valid(value, pattern):
    if not value:
        return False
    return pattern is None or re.fullmatch(pattern, value) is not None


def mask(value):
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def ask_yes_no(prompt, default=True):
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


def prompt_value(name, description, pattern, secret):
    # getpass reads the console directly, so only use it in an interactive terminal
    hide = secret and sys.stdin.isatty()
    reader = getpass.getpass if hide else input
    hint = " (input hidden)" if hide else ""
    while True:
        value = normalize(name, reader(f"  Enter {name}{hint}: "))
        if is_valid(value, pattern):
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
            if is_valid(current, pattern):
                print(f"  Current value: {shown}")
                if ask_yes_no("  Keep it?"):
                    result[name] = current
                    continue
            else:
                print(f"  Current value {shown} doesn't match the expected format.")
                if not ask_yes_no("  Replace it?"):
                    result[name] = current
                    continue
        else:
            print("  Not set.")
        result[name] = prompt_value(name, description, pattern, secret)
    return result


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_env(values, extras):
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
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def backup(path):
    if path.exists():
        backup_path = path.with_name(path.name + ".bak")
        shutil.copy2(path, backup_path)
        print(f"Backed up existing {path.name} to {backup_path.name}")


def heading(title):
    print(f"\n{'=' * 50}\n{title}\n{'=' * 50}")


def setup_packages():
    heading("Step 1: Python packages")
    print(f"Python: {sys.executable}")
    if sys.prefix == sys.base_prefix:
        print("Note: no virtual environment is active, packages will install globally.")
    if not REQUIREMENTS_PATH.exists():
        print(f"{REQUIREMENTS_PATH} not found, skipping.")
        return
    if not ask_yes_no(f"Install packages from {REQUIREMENTS_PATH.name} with pip?"):
        print("Skipped package install.")
        return

    # Use this interpreter's pip so packages land where the bot will run from
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])
    if result.returncode == 0:
        print("Packages installed.")
    else:
        print(f"pip exited with code {result.returncode}. Fix the error above and rerun, "
              "or install manually with:")
        print(f'  "{sys.executable}" -m pip install -r "{REQUIREMENTS_PATH}"')
        if not ask_yes_no("Continue with the rest of setup?"):
            raise SystemExit(1)


def setup_env():
    heading("Step 2: .env")
    print(f"Target: {ENV_PATH}")

    existing = parse_env(ENV_PATH)
    if ENV_PATH.exists():
        valid = sum(1 for name, _, pattern, _ in VARIABLES if is_valid(existing.get(name, ""), pattern))
        print(f"Found existing .env with {valid}/{len(VARIABLES)} required values set and valid.")
        if valid == len(VARIABLES) and not ask_yes_no("Everything looks good. Review the values anyway?", default=False):
            return
    else:
        print("No .env found, a new one will be created.")

    values = collect(existing)

    known_names = {name for name, *_ in VARIABLES}
    extras = {k: v for k, v in existing.items() if k not in known_names}

    print("\nSummary:")
    for name, _, _, secret in VARIABLES:
        print(f"  {name} = {mask(values[name]) if secret else values[name]}")
    if extras:
        print(f"  (+{len(extras)} other value(s) kept: {', '.join(extras)})")

    if not ask_yes_no(f"\nWrite these to {ENV_PATH.name}?"):
        print(f"Skipped, {ENV_PATH.name} not written.")
        return

    backup(ENV_PATH)
    write_env(values, extras)
    print(f"Wrote {ENV_PATH}")


def load_players():
    if not PLAYERS_PATH.exists():
        return []
    try:
        with open(PLAYERS_PATH, "rb") as players_file:
            return tomllib.load(players_file).get("player", [])
    except tomllib.TOMLDecodeError as error:
        print(f"Couldn't read {PLAYERS_PATH.name}: {error}")
        if ask_yes_no("Start from an empty player list instead?"):
            return []
        raise SystemExit(f"Fix {PLAYERS_PATH.name} by hand and rerun setup.")


def describe_player(player):
    discord_id = player.get("discord_id")
    return player["riot_id"] + (f" (Discord {discord_id})" if discord_id else "")


def print_players(players):
    if not players:
        print("  No players yet.")
    for index, player in enumerate(players, 1):
        print(f"  {index}. {describe_player(player)}")


def prompt_player(players):
    taken = {p["riot_id"].lower() for p in players}
    while True:
        riot_id = input("  Riot ID (Name#Tag, blank to cancel): ").strip()
        if not riot_id:
            return None
        if not re.fullmatch(RIOT_ID, riot_id):
            print("  That doesn't look right. Expected Name#Tag, e.g. Faker#KR1 "
                  "(name 3-16 characters, tag 3-5 letters/digits).")
            continue
        if riot_id.lower() in taken:
            print(f"  {riot_id} is already in the list.")
            continue
        break

    player = {"riot_id": riot_id}
    while True:
        discord_id = input("  Discord user ID (optional, blank to skip): ").strip()
        if not discord_id:
            break
        if re.fullmatch(SNOWFLAKE, discord_id):
            player["discord_id"] = discord_id
            break
        print("  Discord IDs are 17-20 digits (right click the user > Copy User ID "
              "with developer mode on).")
    return player


def prompt_removal(players):
    while True:
        choice = input(f"  Number to remove (1-{len(players)}, blank to cancel): ").strip()
        if not choice:
            return
        if choice.isdigit() and 1 <= int(choice) <= len(players):
            removed = players.pop(int(choice) - 1)
            print(f"  Removed {removed['riot_id']}.")
            return
        print("  Not a valid number.")


def write_players(players):
    lines = [
        "# Generated by scripts/setup.py. One [[player]] block per person.",
        "# riot_id is the in-game Name#Tag. discord_id is optional.",
    ]
    for player in players:
        lines.append("")
        lines.append("[[player]]")
        lines.append(f"riot_id = {quote(player['riot_id'])}")
        if player.get("discord_id"):
            lines.append(f"discord_id = {quote(player['discord_id'])}")
    PLAYERS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def setup_players():
    heading("Step 3: players.toml")
    print(f"Target: {PLAYERS_PATH}")

    original = load_players()
    players = [dict(p) for p in original]
    if not PLAYERS_PATH.exists():
        print("No players.toml found, a new one will be created.")

    while True:
        print(f"\nTracked players ({len(players)}):")
        print_players(players)
        choice = input("\n[a]dd, [r]emove, or [d]one? ").strip().lower()
        if choice in ("a", "add"):
            player = prompt_player(players)
            if player:
                players.append(player)
                print(f"  Added {describe_player(player)}.")
        elif choice in ("r", "remove"):
            if players:
                prompt_removal(players)
            else:
                print("  Nothing to remove.")
        elif choice in ("d", "done", ""):
            if not players and not ask_yes_no("  No players added, the ranked job needs at least one. Finish anyway?", default=False):
                continue
            break
        else:
            print("  Please answer a, r, or d.")

    if players == original and PLAYERS_PATH.exists():
        print("No changes to players.toml.")
        return
    if not ask_yes_no(f"\nWrite {len(players)} player(s) to {PLAYERS_PATH.name}?"):
        print(f"Skipped, {PLAYERS_PATH.name} not written.")
        return

    backup(PLAYERS_PATH)
    write_players(players)
    print(f"Wrote {PLAYERS_PATH}")


def setup_dirs():
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
    setup_packages()
    setup_env()
    setup_players()
    setup_dirs()
    print("\nSetup complete.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Anything not yet written was discarded.")
        sys.exit(1)
