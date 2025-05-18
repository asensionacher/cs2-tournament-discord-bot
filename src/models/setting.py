from dataclasses import dataclass
from typing import Optional

@dataclass
class Setting:
    """
    Represents a setting assigned for configuring the bot.
    """
    id: Optional[int] = None
    guild_id: int = 0
    key: str = ""
    value: str = ""