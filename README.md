# Things to improve on

- Containerize

# Setup

```
pip install -r requirements.txt
cp .env.example .env                    # API keys, channel IDs, email
cp players.example.toml players.toml    # who's in the ranked race
```

To add someone, add a `[[player]]` block to `players.toml`. `data/state.json` is written by the job; don't edit it by hand.

Coming from the old `data.py` setup? Run `python migrate_data.py` once instead of copying the examples.

# How to run

```
python runner.py {optional: debug}
```
