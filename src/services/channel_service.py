from typing import List, Optional
from sqlite3 import Connection
from models.channel import Channel

class ChannelService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_channel(self, channel: Channel) -> int:
        """Insert a new channel, returns channel ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO channel (guild_id, channel_name, channel_id)
            VALUES (?, ?, ?)
            """,
            (channel.guild_id, channel.channel_name, channel.channel_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        """Fetch a channel by ID"""
        row = self.conn.execute(
            "SELECT * FROM channel WHERE id = ?", 
            (channel_id,)
        ).fetchone()
        return Channel(*row) if row else None

    def get_channel_by_name(self, channel_name: str, guild_id: str) -> Optional[Channel]:
        """Fetch a channel by channel_name for a guild id"""
        row = self.conn.execute(
            "SELECT * FROM channel WHERE channel_name = ? AND guild_id = ?", 
            (channel_name, guild_id)
        ).fetchone()
        return Channel(*row) if row else None

    def get_all_categories(self, guild_id:str) -> List[Channel]:
        """Fetch all categories for a guild"""
        return [
            Channel(*row) 
            for row in self.conn.execute("SELECT * FROM channel WHERE guild_id = ?",
                                         (guild_id,))
        ]
    
    
    def update_channel(self, channel: Channel):
        """Update channel values"""
        cursor = self.conn.execute(
            """
            UPDATE channel SET guild_id = ?, channel_name = ?, channel_id = ? 
            WHERE id = ?
            """,
            (channel.guild_id, channel.channel_name, channel.channel_id, channel.id)
        )
        self.conn.commit()
        return
    
    def delete_channel(self, id: int):
        """Update server role values"""
        cursor = self.conn.execute(
            """
            DELETE FROM channel
            WHERE id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return