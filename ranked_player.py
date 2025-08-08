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
        
    def __repr__(self, top_rank_lp = 0):
        if (self.playerTier == "UNRANKED"):
            return f"{self.playerName} is unranked\n"
        if top_rank_lp == 0 or top_rank_lp - self.find_player_value() == 0:
            return f"{self.playerName} is {self.playerTier} {self.playerRank}, {self.playerLP} LP, and is the leader!\n"
        else:
            return f"{self.playerName} is {self.playerTier} {self.playerRank}, {self.playerLP} LP. {top_rank_lp - self.find_player_value()} LP behind the leader!\n"
            
    
    def __eq__(self, other):
        return self.playerName == other.playerName and self.playerLP == other.playerLP
    
    def find_player_value(self):
        total_value = 0
        
        if (self.playerTier == "UNRANKED"):
            total_value += -1
        elif (self.playerTier == "IRON"):
            total_value += 0
        elif (self.playerTier == "BRONZE"):
            total_value += 400
        elif (self.playerTier == "SILVER"):
            total_value += 800
        elif (self.playerTier == "GOLD"):
            total_value += 1200
        elif (self.playerTier == "PLATINUM"):
            total_value += 1600
        elif (self.playerTier == "DIAMOND"):
            total_value += 2000
        elif (self.playerTier == "MASTER"):
            total_value += 2400
        elif (self.playerTier == "GRANDMASTER"):
            total_value += 2700
            
        if (self.playerRank == "IV"):
            total_value += 0
        elif (self.playerRank == "III"):
            total_value += 100
        elif (self.playerRank == "II"):
            total_value += 200
        elif (self.playerRank == "I"):
            total_value += 300
            
        total_value += self.playerLP
        
        return total_value