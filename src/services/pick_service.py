from typing import List, Optional
from sqlite3 import Connection
from models.pick import Pick, PickType

class PickService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_pick(self, pick: Pick) -> int:
        """Insert a new pick, returns pick ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO pick (guild_id, order_pick, game_id, 
                team_id, map_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pick.guild_id, pick.order_pick, pick.game_id,
             pick.team_id, pick.map_name)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_pickes(self, guild_id: int) -> List[Pick]:
        """Fetch all pickes"""
        return [
            Pick(*row) 
            for row in self.conn.execute("SELECT * FROM pick WHERE guild_id = ?", (guild_id,))
        ]

    def get_all_pickes_by_game(self, guild_id: int, game_id: int) -> List[Pick]:
        """Fetch all pickes by game id"""
        return [
            Pick(*row) 
            for row in self.conn.execute("SELECT * FROM pick WHERE guild_id = ? AND game_id = ?", 
                                         (guild_id, game_id))
        ]

    def delete_pick_by_id(self, id: int):
        """Delete pick by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM pick 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return