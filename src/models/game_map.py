from dataclasses import dataclass
from typing import Optional

@dataclass
class GameMap:
    """
    Represents a map of a game after being played for storing the winner of the map of the game.

    Attributes:
        game_id: Id of the game related to this game map
        team_id_winner: Id of the team that won the map
        guild_id: Discord guild id        
    """
    id: Optional[int] = None
    game_id: int = 0
    team_id_winner: int = 0
    guild_id: int = 0