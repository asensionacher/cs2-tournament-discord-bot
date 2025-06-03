from typing import List, Optional
from sqlite3 import Connection
from models.player import Player

class PlayerService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_player(self, player: Player) -> int:
        """Insert a new player, returns player ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO player (guild_id, role_name, nickname, steamid, team_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (player.guild_id, player.role_name, player.nickname, player.steamid, player.team_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """Fetch a player by ID"""
        row = self.conn.execute(
            "SELECT * FROM player WHERE id = ?", 
            (player_id,)
        ).fetchone()
        return Player(*row) if row else None

    def get_all_players(self) -> List[Player]:
        """Fetch all players"""
        return [
            Player(*row) 
            for row in self.conn.execute("SELECT * FROM player")
        ]

    def get_player_by_nickname(self, nickname: str, guild_id: int) -> List[Player]:
        """Fetch a player by nickname for a guild id"""
        row = self.conn.execute(
            "SELECT * FROM player WHERE nickname = ? AND guild_id = ?", 
            (nickname, guild_id)
        ).fetchone()
        return Player(*row) if row else None

    def get_player_by_steamid(self, steamid: str, guild_id: int) -> List[Player]:
        """Fetch a player by steamid for a guild id"""
        row = self.conn.execute(
            "SELECT * FROM player WHERE steamid = ? AND guild_id = ?", 
            (steamid, guild_id)
        ).fetchone()
        return Player(*row) if row else None    

    def get_players_by_team_id(self, team_id: int) -> List[Player]:
        """Fetch a player by team_id"""
        return [
            Player(*row) 
            for row in self.conn.execute(
            "SELECT * FROM player WHERE team_id = ?", 
            (team_id,)
            )
        ]

    def get_players_by_team_id_and_role_name(self, team_id: int, role_name: str) -> List[Player]:
        """Fetch a player by team_id"""
        return [
            Player(*row) 
            for row in self.conn.execute(
            "SELECT * FROM player WHERE team_id = ? AND role_name = ?", 
            (team_id, role_name)
            )
        ]
    
    def delete_player_by_id(self, id: int):
        """Delete player by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM player 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return