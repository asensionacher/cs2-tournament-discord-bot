from typing import List, Optional
from sqlite3 import Connection
from models.game_map import GameMap

class GameMapService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_game_map(self, game_map: GameMap) -> int:
        """Insert a new game_map, returns game_map ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO game_map (guild_id, team_id_winner, game_number, map_name, game_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_map.guild_id, game_map.team_id_winner, game_map.game_number, game_map.map_name, game_map.game_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_game_maps(self, guild_id: int) -> List[GameMap]:
        """Fetch all game_maps"""
        return [
            GameMap(*row) 
            for row in self.conn.execute("SELECT * FROM game_map WHERE guild_id = ?", (guild_id,))
        ]

    def get_all_game_maps_by_game(self, guild_id: int, game_id: int) -> List[GameMap]:
        """Fetch all game_maps by game id"""
        return [
            GameMap(*row) 
            for row in self.conn.execute("""SELECT * FROM game_map 
                            WHERE guild_id = ? AND game_id = ?
                            ORDER BY game_number ASC""", 
                         (guild_id, game_id))
        ]

    def get_game_map_by_game_and_map_name(self, guild_id: int, game_id: int, map_name: str) -> Optional[GameMap]:
        """Fetch the first game_map with a lower game_number that is not finished"""
        cursor = self.conn.execute("""SELECT * FROM game_map 
                            WHERE guild_id = ? AND game_id = ? AND map_name = ?
                            """, 
                         (guild_id, game_id, map_name))
        row = cursor.fetchone()
        if row:
            return GameMap(*row)
        return None

    def get_first_not_finished_game_map(self, guild_id: int, game_id: int) -> Optional[GameMap]:
        """Fetch the first game_map with a lower game_number that is not finished"""
        cursor = self.conn.execute("""SELECT * FROM game_map 
                            WHERE guild_id = ? AND game_id = ? AND team_id_winner <= 0
                            ORDER BY game_number ASC
                            LIMIT 1""", 
                         (guild_id, game_id))
        row = cursor.fetchone()
        if row:
            return GameMap(*row)
        return None

    def get_last_not_finished_game_map(self, guild_id: int, game_id: int) -> Optional[GameMap]:
        """Fetch the last game_map with a lower game_number that is not finished"""
        cursor = self.conn.execute("""SELECT * FROM game_map 
                    WHERE guild_id = ? AND game_id = ? AND team_id_winner <= 0
                    ORDER BY game_number DESC
                    LIMIT 1""", 
                 (guild_id, game_id))
        row = cursor.fetchone()
        if row:
            return GameMap(*row)
        return None

    def get_by_game_id_game_number_game_map(self, game_id: int, game_number: int) -> Optional[GameMap]:
        """Fetch the first game_map with a lower game_number that is not finished"""
        cursor = self.conn.execute("""SELECT * FROM game_map 
                            WHERE game_id = ? AND game_number = ?
                            """, 
                         (game_id, game_number))
        row = cursor.fetchone()
        if row:
            return GameMap(*row)
        return None


    def delete_game_map_by_id(self, id: int):
        """Delete game_map by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM game_map 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return

    def update_game_map(self, game_map: GameMap):
        """Update game_map"""
        self.conn.execute(
            """
            UPDATE game_map 
            SET guild_id = ?, team_id_winner = ?, game_number = ?, map_name = ?, 
            game_id = ?
            WHERE id = ?
            """,
            (game_map.guild_id, game_map.team_id_winner, game_map.game_number, game_map.map_name, 
             game_map.game_id, 
             game_map.id)
        )
        self.conn.commit()
        return