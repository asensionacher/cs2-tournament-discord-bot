from typing import List, Optional
from sqlite3 import Connection
from models.server_role import ServerRole

class ServerRoleService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_server_role(self, server_role: ServerRole) -> int:
        """Insert a new server_role, returns server_role ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO server_role (guild_id, role_name, role_id)
            VALUES (?, ?, ?)
            """,
            (server_role.guild_id, server_role.role_name, server_role.role_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_server_role_by_id(self, server_role_id: int) -> Optional[ServerRole]:
        """Fetch a server_role by ID"""
        row = self.conn.execute(
            "SELECT * FROM server_role WHERE id = ?", 
            (server_role_id,)
        ).fetchone()
        return ServerRole(*row) if row else None

    def get_server_role_by_name(self, server_role_name: str, guild_id: int) -> Optional[ServerRole]:
        """Fetch a server_role by Name for a guild"""
        row = self.conn.execute(
            "SELECT * FROM server_role WHERE role_name = ? AND guild_id = ?", 
            (server_role_name, guild_id)
        ).fetchone()
        return ServerRole(*row) if row else None

    def get_all_server_roles(self, guild_id: int) -> List[ServerRole]:
        """Fetch all server_roles for a guild"""
        return [
            ServerRole(*row) 
            for row in self.conn.execute("SELECT * FROM server_role WHERE guild_id = ?",
                                          (guild_id,))
        ]
    
    def update_server_role(self, server_role: ServerRole):
        """Update server role values"""
        cursor = self.conn.execute(
            """
            UPDATE server_role SET guild_id = ?, role_name = ?, role_id = ? 
            WHERE id = ?
            """,
            (server_role.guild_id, server_role.role_name, server_role.role_id, server_role.id)
        )
        self.conn.commit()
        return
    
    def delete_server_role(self, id: int):
        """Update server role values"""
        cursor = self.conn.execute(
            """
            DELETE FROM server_role
            WHERE id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return