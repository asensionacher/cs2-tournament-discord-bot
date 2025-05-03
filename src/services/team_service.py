from typing import List, Optional
from sqlite3 import Connection
from models.team import Team

class TeamService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_team(self, team: Team) -> int:
        """Insert a new team, returns team ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO team (name, discord_message_id, guild_id)
            VALUES (?, ?, ?)
            """,
            (team.name, team.discord_message_id, team.guild_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Fetch a team by ID"""
        row = self.conn.execute(
            "SELECT * FROM team WHERE id = ?", 
            (team_id,)
        ).fetchone()
        return Team(*row) if row else None

    def get_all_teams(self, guild_id: int) -> List[Team]:
        """Fetch all teams"""
        return [
            Team(*row) 
            for row in self.conn.execute("SELECT * FROM team WHERE guild_id = ?", (guild_id,))
        ]


    def get_team_by_name(self, name: str, guild_id: int) -> Optional[Team]:
        """Fetch a team by name for a guild id"""
        row = self.conn.execute(
            "SELECT * FROM team WHERE name = ? AND guild_id = ?", 
            (name, guild_id)
        ).fetchone()
        return Team(*row) if row else None
    

    
    def delete_team_by_id(self, id: int):
        """Delete team by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM team 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return