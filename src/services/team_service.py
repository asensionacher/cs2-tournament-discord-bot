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
    

    def get_teams_by_record(self, guild_id: int, wins: int, losses: int) -> List[Team]:
        """Fetch all teams by type"""
        return [
            Team(*row) 
            for row in self.conn.execute("SELECT * FROM team WHERE guild_id = ? AND swiss_wins == ? AND swiss_losses = ?", 
                                        (guild_id, wins, losses))
        ]

    def get_teams_quaterfinalist(self, guild_id: int, ) -> List[Team]:
        """Fetch all teams by type"""
        return [
            Team(*row) 
            for row in self.conn.execute("SELECT * FROM team WHERE guild_id = ? AND is_quaterfinalist == ? ", 
                                        (guild_id, True))
        ]

    def get_teams_semifinalist(self, guild_id: int, ) -> List[Team]:
        """Fetch all teams by type"""
        return [
            Team(*row) 
            for row in self.conn.execute("SELECT * FROM team WHERE guild_id = ? AND is_semifinalist == ? ", 
                                        (guild_id, True))
        ]

    def get_teams_finalist(self, guild_id: int, ) -> List[Team]:
        """Fetch all teams by type"""
        return [
            Team(*row) 
            for row in self.conn.execute("SELECT * FROM team WHERE guild_id = ? AND is_finalist == ? ", 
                                        (guild_id, True))
        ]

    def get_teams_third_place(self, guild_id: int, ) -> List[Team]:
        """Fetch all teams by type"""
        return [
            Team(*row) 
            for row in self.conn.execute("SELECT * FROM team WHERE guild_id = ? AND is_third_place == ? ", 
                                        (guild_id, True))
        ]
    
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

    def update_team(self, team: Team):
        """Update an existing team"""
        self.conn.execute(
            """
            UPDATE team 
            SET name = ?, discord_message_id = ?, swiss_wins = ?,
                swiss_losses = ?, guild_id = ?, is_quaterfinalist = ?,
                is_semifinalist = ?, is_finalist = ?, is_third_place = ?
            WHERE id = ?
            """,
            (team.name, team.discord_message_id, team.swiss_wins,
             team.swiss_losses, team.guild_id, team.is_quaterfinalist,
             team.is_semifinalist, team.is_finalist, team.is_third_place,
             team.id)
        )
        self.conn.commit()
