import sys
from messageGroup import messageGroup

# Arg 1 : Riot Api Key
# Arg 2 : Discord Bot Api Key
# Arg 3 : (Optional) Debug Flag
def main():
    if len(sys.argv) > 2:
        riot_api_key = sys.argv[1]
        discord_bot_api_key = sys.argv[2]
        
        debugFlag = False
        if len(sys.argv) > 3:
            debugFlag = sys.argv[3] == "debug"

        messageGroup(riot_api_key, discord_bot_api_key, debugFlag)
    else:
        print("No Riot Api Key or Discord Api Key Provided")

if __name__ == "__main__":
    main()