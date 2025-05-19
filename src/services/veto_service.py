from typing import List, Optional
from sqlite3 import Connection
from models.veto import Veto

class VetoService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_veto(self, veto: Veto) -> int:
        """Insert a new veto, returns veto ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO veto (guild_id, order_veto, game_id, 
                team_id, map_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (veto.guild_id, veto.order_veto, veto.game_id,
             veto.team_id, veto.map_name)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_vetoes(self, guild_id: int) -> List[Veto]:
        """Fetch all vetoes"""
        return [
            Veto(*row) 
            for row in self.conn.execute("SELECT * FROM veto WHERE guild_id = ?", (guild_id,))
        ]

    def get_all_vetoes_by_game(self, guild_id: int, game_id: int) -> List[Veto]:
        """Fetch all vetoes by game id"""
        return [
            Veto(*row) 
            for row in self.conn.execute("SELECT * FROM veto WHERE guild_id = ? AND game_id = ?", 
                                         (guild_id, game_id))
        ]

    def get_all_vetoes_by_game_id_only(self, game_id: int) -> List[Veto]:
        """Fetch all vetoes by game id"""
        return [
            Veto(*row) 
            for row in self.conn.execute("SELECT * FROM veto WHERE game_id = ?", 
                                         (game_id, ))
        ]

    def delete_veto_by_id(self, id: int):
        """Delete veto by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM veto 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return