from dataclasses import dataclass
from typing import Optional

@dataclass
class Team:
    """
    Represents a Team that will compete in the tournament
    """
    id: Optional[int] = None
    name: str = ""
    discord_message_id: Optional[int] = None
    guild_id: Optional[int] = None