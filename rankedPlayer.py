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
    # Tiers above diamond have no divisions, Riot always reports them as "I"
    APEX_TIERS = ("MASTER", "GRANDMASTER", "CHALLENGER")

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
        rankText = self.playerTier if self.playerTier in self.APEX_TIERS else f"{self.playerTier} {self.playerRank}"
        if topRankLp == 0 or topRankLp - self.findPlayerValue() == 0:
            return f"{symbol} {self.playerName} is {rankText}, {self.playerLP} LP, and is the leader!\n"
        else:
            return (
                f"{symbol} {self.playerName} is {rankText}, {self.playerLP} LP. "
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
            totalValue += 2400
        # Apex elos all work as master + LP, so we set it as the same as Diamond I 100LP + their total LP
        elif self.playerTier in self.APEX_TIERS:
            totalValue += 2800
            totalValue += self.playerLP
            return totalValue

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
