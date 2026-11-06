# Things to improve on

- Containerize

# Setup

```
python ./scripts/setup.py
```

To add someone, use the setup script or add a `[[player]]` block to `config/players.toml`. `data/state/state.json` is written by the job; don't edit it by hand.

Coming from the old `data.py` setup? Run `python ./scripts/migrate_data.py` once instead of copying the examples.

# How to run

```
python runner.py {optional: debug}
```

# Linting

[Ruff](https://docs.astral.sh/ruff/) lints and formats the code.

To check or fix by hand:
```
ruff check --fix        # lint, auto-fixing what's safe
ruff format             # format
pre-commit run --all-files
```
