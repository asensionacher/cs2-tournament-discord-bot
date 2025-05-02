from dataclasses import dataclass
from typing import Optional

@dataclass
class Category:
    """
    Represents a created category in discord.

    Attributes:
        guild_id: Discord guild id
        category_name: Name of the created category
        category_id: Discord id of the category created.
    """
    id: Optional[int] = None
    guild_id: int = 0
    category_name: str = ""
    category_id: int = 0