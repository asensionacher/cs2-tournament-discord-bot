from typing import List, Optional
from sqlite3 import Connection
from models.setting import Setting

class SettingService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_setting(self, setting: Setting) -> int:
        """Insert a new setting, returns setting ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO setting (key, value, guild_id)
            VALUES (?, ?, ?)
            """,
            (setting.key, setting.value, setting.guild_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_setting_by_id(self, setting_id: int) -> Optional[Setting]:
        """Fetch a setting by ID"""
        row = self.conn.execute(
            "SELECT * FROM setting WHERE id = ?", 
            (setting_id,)
        ).fetchone()
        return Setting(*row) if row else None

    def get_setting_by_name(self, setting_key: str, guild_id: int) -> Optional[Setting]:
        """Fetch a setting by Key"""
        row = self.conn.execute(
            "SELECT * FROM setting WHERE key = ? AND guild_id = ?", 
            (setting_key, guild_id)
        ).fetchone()
        return Setting(*row) if row else None

    def get_all_settings(self, guild_id: int) -> List[Setting]:
        """Fetch all settings"""
        return [
            Setting(*row) 
            for row in self.conn.execute("SELECT * FROM setting WHERE guild_id = ?",
                                         (guild_id,))
        ]
    
    def delete_all_settings(self, guild_id: int):
        """Delete all settings of a guild"""
        cursor = self.conn.execute(
            """
            DELETE FROM setting 
            where guild_id = ?
            """,
            (guild_id,)
        )
        self.conn.commit()
        return