from dataclasses import dataclass
from typing import Optional

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
    role_name: str = "player"  # 'captain', 'player', or 'coach'