# Things to improve on

- Containerize

# Setup

```
python ./scripts/setup.py
```

To add someone, use the setup script or add a `[[player]]` block to `players.toml`. `data/state.json` is written by the job; don't edit it by hand.

Coming from the old `data.py` setup? Run `python migrate_data.py` once instead of copying the examples.

# How to run

```
python runner.py {optional: debug}
```
