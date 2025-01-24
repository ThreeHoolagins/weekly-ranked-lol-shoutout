import sys
from messageGroup import messageGroup

# Arg 1 : Api Key
# Arg 2 : Server Hash
def main():
    if len(sys.argv) > 2:
        riot_api_key = sys.argv[1]
        discord_bot_api_key = sys.argv[2]
        # print(f"First argument: {riot_api_key}")
        # print(f"Second argument: {discord_bot_api_key}")
        messageGroup(riot_api_key, discord_bot_api_key)
    else:
        print("No Riot Api Key or Discord Api Key Provided")

if __name__ == "__main__":
    main()