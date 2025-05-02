from typing import List, Optional
from sqlite3 import Connection
from ..models.category import Category

class CategoryService:
    def __init__(self, conn: Connection):
        self.conn = conn

    def create_category(self, category: Category) -> int:
        """Insert a new category, returns category ID"""
        cursor = self.conn.execute(
            """
            INSERT INTO category (guild_id, category_name, category_id)
            VALUES (?, ?, ?)
            """,
            (category.guild_id, category.category_name, category.category_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Fetch a category by ID"""
        row = self.conn.execute(
            "SELECT * FROM category WHERE id = ?", 
            (category_id,)
        ).fetchone()
        return Category(*row) if row else None

    def get_category_by_name(self, category_name: str, guild_id: str) -> Optional[Category]:
        """Fetch a category by category_name for a guild id"""
        row = self.conn.execute(
            "SELECT * FROM category WHERE category_name = ? AND guild_id = ?", 
            (category_name, guild_id)
        ).fetchone()
        return Category(*row) if row else None

    def get_all_categories(self, guild_id:str) -> List[Category]:
        """Fetch all categories for a guild"""
        return [
            Category(*row) 
            for row in self.conn.execute("SELECT * FROM category WHERE guild_id = ?",
                                         (guild_id,))
        ]
    
    
    def update_category(self, category: ServerRole):
        """Update category values"""
        cursor = self.conn.execute(
            """
            UPDATE category SET guild_id = ?, category_name = ?, category_id = ? 
            WHERE id = ?
            """,
            (category.guild_id, category.category_name, category.category_id, category.id)
        )
        self.conn.commit()
        return
    
    def delete_category(self, id: int):
        """Update server role values"""
        cursor = self.conn.execute(
            """
            DELETE FROM category
            WHERE id = ?
            """,
            (id,)
        )
        self.conn.commit()
        return