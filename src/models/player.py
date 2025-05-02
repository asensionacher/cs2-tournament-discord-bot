from dataclasses import dataclass
from typing import Optional
from enum import Enum

@dataclass
class PlayerRole(Enum):
    """
    Player roles allowed to be added to the player.
    """
    CAPTAIN = "captain"
    PLAYER = "player"
    COACH = "coach"

@dataclass
class Player:
    """
    Player assigned to a team
    """
    id: Optional[int] = None
    guild_id: Optional[int] = None
    team_id: Optional[int] = None
    nickname: str = ""
    steamid: str = ""
    role_name: PlayerRole  # 'captain', 'player', or 'coach'