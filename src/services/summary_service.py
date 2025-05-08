from typing import List, Optional
from sqlite3 import Connection
from models.summary import Summary

class SummaryService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_summary(self, summary: Summary) -> int:
        """Insert a new summary, returns summary ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO summary (guild_id, round, public_game_message_id)
            VALUES (?, ?, ?)
            """,
            (summary.guild_id, summary.round, summary.public_game_message_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_summaries(self, guild_id: int) -> List[Summary]:
        """Fetch all summaries"""
        return [
            Summary(*row) 
            for row in self.conn.execute("SELECT * FROM summary WHERE guild_id = ?", (guild_id,))
        ]

    def get_all_summaries_by_round(self, guild_id: int, round: str) -> List[Summary]:
        """Fetch all summaries by game id"""
        return [
            Summary(*row) 
            for row in self.conn.execute("SELECT * FROM summary WHERE guild_id = ? AND round = ?", 
                                         (guild_id, round))
        ]

    def delete_summary_by_id(self, id: int):
        """Delete summary by id"""
        cursor = self.conn.execute(
            """
            DELETE FROM summary 
            where id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return