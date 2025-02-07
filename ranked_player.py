class ranked_player:
    
    TIER_ORDER = ['UNRANKED', 'IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER']
    RANK_ORDER = ['IV', 'III', 'II', 'I']
    
    def __init__(self, playerName, playerTier, playerRank, playerLP):
        self.playerName = playerName
        self.playerTier = playerTier
        self.playerRank = playerRank
        self.playerLP = int(playerLP)
        
    def __lt__(self, other):
        if self.find_player_value() < other.find_player_value():
            return False
        else:
            return True
        
    def __repr__(self):
        if (self.playerTier == "UNRANKED"):
            return f"{self.playerName} is unranked\n"
        return f"{self.playerName} is {self.playerTier} {self.playerRank}, {self.playerLP} LP\n"
    
    def find_player_value(self):
        total_value = 0
        
        if (self.playerTier == "UNRANKED"):
            total_value += 0
        elif (self.playerTier == "IRON"):
            total_value += 1000
        elif (self.playerTier == "BRONZE"):
            total_value += 2000
        elif (self.playerTier == "SILVER"):
            total_value += 3000
        elif (self.playerTier == "GOLD"):
            total_value += 4000
        elif (self.playerTier == "PLATINUM"):
            total_value += 5000
        elif (self.playerTier == "DIAMOND"):
            total_value += 6000
        elif (self.playerTier == "MASTER"):
            total_value += 7000
        elif (self.playerTier == "GRANDMASTER"):
            total_value += 8000
            
        if (self.playerRank == "IV"):
            total_value += 200
        elif (self.playerRank == "III"):
            total_value += 400
        elif (self.playerRank == "II"):
            total_value += 600
        elif (self.playerRank == "I"):
            total_value += 800
            
        total_value += self.playerLP
        
        return total_value