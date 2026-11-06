class rankedPlayer:
    TIER_ORDER = (
        "UNRANKED",
        "IRON",
        "BRONZE",
        "SILVER",
        "GOLD",
        "PLATINUM",
        "EMERALD",
        "DIAMOND",
        "MASTER",
        "GRANDMASTER",
        "CHALLENGER",
    )
    RANK_ORDER = ("IV", "III", "II", "I")

    def __init__(self, puuid, playerName, playerTier, playerRank, playerLP):
        self.puuid = puuid
        self.playerName = playerName
        self.playerTier = playerTier
        self.playerRank = playerRank
        self.playerLP = int(playerLP)

    def __lt__(self, other):
        return not self.findPlayerValue() < other.findPlayerValue()

    def __eq__(self, other):
        return self.puuid == other.puuid and self.findPlayerValue() == other.findPlayerValue()

    def __repr__(self, topRankLp=0, oldPlayer=None):
        if oldPlayer is not None and self.puuid != oldPlayer.puuid:
            raise ValueError(
                f"Player mismatch in __repr__: current '{self.playerName}' != old '{oldPlayer.playerName}'"
            )

        # abstract this maybe? setting?
        if oldPlayer is None or self.findPlayerValue() == oldPlayer.findPlayerValue():
            symbol = "\u2013"
        elif self.findPlayerValue() > oldPlayer.findPlayerValue():
            symbol = "\u001b[1;32m\u25b2\u001b[0m"
        else:
            symbol = "\u001b[1;31m\u25bc\u001b[0m"

        if self.playerTier == "UNRANKED":
            return f"{self.playerName} is unranked\n"
        if topRankLp == 0 or topRankLp - self.findPlayerValue() == 0:
            return (
                f"{symbol} {self.playerName} is {self.playerTier} {self.playerRank}, "
                f"{self.playerLP} LP, and is the leader!\n"
            )
        else:
            return (
                f"{symbol} {self.playerName} is {self.playerTier} {self.playerRank}, {self.playerLP} LP. "
                f"{topRankLp - self.findPlayerValue()} LP behind the leader!\n"
            )

    def findPlayerValue(self):
        totalValue = 0

        if self.playerTier == "UNRANKED":
            totalValue += -1
        elif self.playerTier == "IRON":
            totalValue += 0
        elif self.playerTier == "BRONZE":
            totalValue += 400
        elif self.playerTier == "SILVER":
            totalValue += 800
        elif self.playerTier == "GOLD":
            totalValue += 1200
        elif self.playerTier == "PLATINUM":
            totalValue += 1600
        elif self.playerTier == "EMERALD":
            totalValue += 2000
        elif self.playerTier == "DIAMOND":
            totalValue += 2200
        elif self.playerTier == "MASTER":
            totalValue += 2600
        # Grandmaster and challenger are not fixed size ranks (ex. 400lp more than diamond),
        # they are fixed player pools (500 for grandmaster, 200 for challenger)
        elif self.playerTier == "GRANDMASTER":
            totalValue += 3000
        elif self.playerTier == "CHALLENGER":
            totalValue += 4000

        if self.playerRank == "IV":
            totalValue += 0
        elif self.playerRank == "III":
            totalValue += 100
        elif self.playerRank == "II":
            totalValue += 200
        elif self.playerRank == "I":
            totalValue += 300

        totalValue += self.playerLP

        return totalValue
