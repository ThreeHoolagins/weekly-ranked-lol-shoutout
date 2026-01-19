import sqlite3

from data import SQLITE_PATH

def get_conn():
    conn = sqlite3.connect(SQLITE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS player_games_link (
            id INTEGER PRIMARY KEY,
            puuid TEXT NOT NULL,
            game_id TEXT NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS games_data (
            id INTEGER PRIMARY KEY,
            game_id TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            info_json TEXT NOT NULL
        );
        """)
        conn.commit()
        
def get_game_ids(puuid):
    with get_conn() as conn:
        cur = conn.cursor()
        res = cur.execute("SELECT game_id FROM player_games_link WHERE puuid = ?", (puuid,))
        rows = res.fetchall()
        return [list(row)[0] for row in rows]
    
def insert_game_ids(puuid, games):
    with get_conn() as conn:
        cur = conn.cursor()
        data = [(puuid, game) for game in games]
        cur.executemany("INSERT INTO player_games_link (puuid, game_id) VALUES (?, ?)", data)
        conn.commit()
    
    
if __name__ == "__main__":
    print("DB Test in progress")
    init_database()
    print(get_game_ids("testPerson2"))
    insert_game_ids("testPerson2", ["testGameId10", "testGameId20"])
    print(get_game_ids("testPerson2"))