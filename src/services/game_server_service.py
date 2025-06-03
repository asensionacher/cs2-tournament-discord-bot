from typing import List, Optional
from sqlite3 import Connection
from models.game_server import GameServer

class GameServerService:
    def __init__(self, conn: Connection):
        self.conn = conn

    id: Optional[int] = None
    guild_id: int = 0
    ip: str = ""
    game_port: int = 0
    rcon_password: str = ""
    cstv_port: int = 0
    is_free: bool = True
    def create_game_server(self, game_server: GameServer) -> int:
        """Insert a new game_server, returns game_server ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO game_server (guild_id, ip, game_port, rcon_password, cstv_port, is_free, game_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (game_server.guild_id, game_server.ip, game_server.game_port, 
             game_server.rcon_password, game_server.cstv_port, game_server.is_free,
             game_server.game_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_game_server_by_id(self, game_server_id: int) -> Optional[GameServer]:
        """Fetch a game_server by ID"""
        row = self.conn.execute(
            "SELECT * FROM game_server WHERE id = ?", 
            (game_server_id,)
        ).fetchone()
        return GameServer(*row) if row else None

    def get_game_server_by_ip(self, ip: str) -> Optional[GameServer]:
        """Fetch a game_server by ip"""
        row = self.conn.execute(
            "SELECT * FROM game_server WHERE ip = ?", 
            (ip,)
        ).fetchone()
        return GameServer(*row) if row else None

    def get_game_server_by_game_id(self, game_id: int) -> Optional[GameServer]:
        """Fetch a game_server by ip"""
        row = self.conn.execute(
            "SELECT * FROM game_server WHERE game_id = ?", 
            (game_id,)
        ).fetchone()
        return GameServer(*row) if row else None

    def get_all_game_servers(self, guild_id: int) -> List[GameServer]:
        """Fetch all game_servers"""
        return [
            GameServer(*row) 
            for row in self.conn.execute("SELECT * FROM game_server WHERE guild_id = ?",
                                         (guild_id,))
        ]
    
    def get_free_game_server(self, guild_id: int) -> List[GameServer]:
        """Fetch first free game_server"""
        cursor = self.conn.execute("""
                                    SELECT * FROM game_server
                                    WHERE guild_id = ? AND is_free = TRUE
                                    LIMIT 1""",
                                    (guild_id,))
        row = cursor.fetchone()
        if row:
            return GameServer(*row)
        return None
    
    def get_game_server_by_game_id(self, game_id: int) -> List[GameServer]:
        """Fetch first free game_server"""
        cursor = self.conn.execute("""
                                    SELECT * FROM game_server
                                    WHERE game_id = ?""",
                                    (game_id,))
        row = cursor.fetchone()
        if row:
            return GameServer(*row)
        return None
    
    def delete_all_game_servers(self, guild_id: int):
        """Delete all game_servers of a guild"""
        cursor = self.conn.execute(
            """
            DELETE FROM game_server 
            where guild_id = ?
            """,
            (guild_id,)
        )
        self.conn.commit()
        return
    
    def delete_game_server_by_id(self, id: int):
        """Delete game_server by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM game_server 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return

    def update_game_server(self, game_server: GameServer):
        """Update a game_server"""
        cursor = self.conn.execute(
            """
            UPDATE game_server 
            SET guild_id = ?, ip = ?, game_port = ?, rcon_password = ?, cstv_port = ?, is_free = ?, game_id = ?
            WHERE id = ?
            """,
            (game_server.guild_id, game_server.ip, game_server.game_port, 
             game_server.rcon_password, game_server.cstv_port, game_server.is_free, game_server.game_id,
             game_server.id)
        )
        self.conn.commit()