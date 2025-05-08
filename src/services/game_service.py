from typing import List, Optional
from sqlite3 import Connection
from models.game import Game

class GameService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_game(self, game: Game) -> int:
        """Insert a new game, returns game ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO game (guild_id, team_one_id, team_two_id, 
                game_type, game_channel_id, admin_game_channel_id,
                voice_channel_team_one_id, voice_channel_team_two_id,
                public_game_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (game.guild_id, game.team_one_id, game.team_two_id,
             game.game_type, game.game_channel_id, game.admin_game_channel_id,
             game.voice_channel_team_one_id, game.voice_channel_team_two_id, 
             game.public_game_message_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        """Fetch a game by ID"""
        row = self.conn.execute(
            "SELECT * FROM game WHERE id = ?", 
            (game_id,)
        ).fetchone()
        return Game(*row) if row else None

    def get_all_games(self, guild_id: int) -> List[Game]:
        """Fetch all games"""
        return [
            Game(*row) 
            for row in self.conn.execute("SELECT * FROM game WHERE guild_id = ?", (guild_id,))
        ]

    def get_all_games_finished(self, guild_id: int) -> List[Game]:
        """Fetch all games"""
        return [
            Game(*row) 
            for row in self.conn.execute("SELECT * FROM game WHERE guild_id = ? AND team_winner > 0", (guild_id,))
        ]

    def get_all_games_not_finished(self, guild_id: int) -> List[Game]:
        """Fetch all games"""
        return [
            Game(*row) 
            for row in self.conn.execute("SELECT * FROM game WHERE guild_id = ? AND team_winner <= 0", (guild_id,))
        ]

    def get_games_by_type(self, game_type: str, guild_id: int) -> List[Game]:
        """Fetch games by type for a guild id"""
        return [
            Game(*row) 
            for row in self.conn.execute("SELECT * FROM game WHERE game_type = ?  AND guild_id = ?", (game_type, guild_id))
        ]

    def get_game_by_teams_and_type(self, team_one_id: int, team_two_id:int, 
                                   game_type: str, guild_id: int) -> Optional[Game]:
        """Fetch a game by teams and type for a guild id"""
        row = self.conn.execute(
            """
            SELECT * FROM game WHERE (team_one_id = ? AND team_two_id = ?)
            OR (team_one_id = ? AND team_two_id = ?)
            AND game_type = ?
            AND guild_id = ?
            """, 
            (team_one_id, team_two_id, team_two_id, team_one_id, game_type, guild_id)
        ).fetchone()
        return Game(*row) if row else None
    
    def get_game_by_admin_game_channel_id(self, admin_game_channel_id: int) -> Optional[Game]:
        """Fetch a game by admin game channel ID"""
        row = self.conn.execute(
            """
            SELECT * FROM game WHERE admin_game_channel_id = ?
            """, 
            (admin_game_channel_id,)
        ).fetchone()
        print(f"row -> {row}")
        return Game(*row) if row else None

    def get_all_games_by_type(self, guild_id: int, game_type: str) -> List[Game]:
        """Fetch all games by type"""
        return [
            Game(*row) 
            for row in self.conn.execute("SELECT * FROM game WHERE guild_id = ? AND game_type == ?", 
                                        (guild_id, game_type))
        ]    

    def delete_game_by_id(self, id: int):
        """Delete game by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM game 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return
    
    def update_game(self, game: Game):
        """Update an existing game"""
        self.conn.execute(
            """
            UPDATE game SET guild_id = ?, team_one_id = ?, team_two_id = ?, 
            game_type = ?, game_channel_id = ?, admin_game_channel_id = ?,
            voice_channel_team_one_id = ?, voice_channel_team_two_id = ?,
            public_game_message_id = ?, team_winner = ?
            WHERE id = ?
            """,
            (game.guild_id, game.team_one_id, game.team_two_id,
             game.game_type, game.game_channel_id, game.admin_game_channel_id,
             game.voice_channel_team_one_id, game.voice_channel_team_two_id, 
             game.public_game_message_id, game.team_winner, game.id)
        )
        self.conn.commit()
