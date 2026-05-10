import duckdb
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

class UserCache:
    def __init__(self, db_path: str = "outputs/user_cache.duckdb"):
        # Ensure the outputs directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path: str = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Creates the cache table if it doesn't already exist."""
        with duckdb.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_games (
                    username VARCHAR PRIMARY KEY,
                    games_json TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def get_games(self, username: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches the user's games from the DuckDB cache."""
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT games_json FROM user_games WHERE LOWER(username) = LOWER(?)", 
                [username]
            ).fetchone()
            
            if result:
                return json.loads(result[0])
            return None

    def save_games(self, username: str, games: List[Dict[str, Any]]) -> None:
            """Saves or updates the user's games in the DuckDB cache."""
            games_str = json.dumps(games)
            
            # Capture the current time in Python instead of SQL
            current_time = datetime.now().isoformat() 
            
            with duckdb.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_games (username, games_json, last_updated)
                    VALUES (?, ?, ?)
                    ON CONFLICT (username) DO UPDATE 
                    SET games_json = EXCLUDED.games_json,
                        last_updated = ?
                """, [username, games_str, current_time, current_time])
