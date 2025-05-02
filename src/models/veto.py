from dataclasses import dataclass
from typing import Optional

@dataclass
class Veto:
    """
    Veto of a map in the pick and bans phase
    """
    id: Optional[int] = None
    order_veto: int = 0
    game_id: int = 0
    team_id: int = 0
    map_name: str = ""
    guild_id: int = 0