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
    swiss_wins: int = 0
    swiss_losses: int = 0
    guild_id: Optional[int] = None
    is_quarterfinalist: bool = False
    is_semifinalist: bool = False
    is_finalist: bool = False
    is_third_place: bool = False