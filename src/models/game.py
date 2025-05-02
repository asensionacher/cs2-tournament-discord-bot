from dataclasses import dataclass
from typing import Optional
from enum import Enum

@dataclass
class GameType(Enum):
    """
    Game types allowed to be added to the game class.
    """
    SWISS_1 = "swiss_1"
    SWISS_2 = "swiss_2"
    SWISS_3 = "swiss_3"
    SWISS_4 = "swiss_4"
    SWISS_5 = "swiss_5"
    QUARTERFINAL = "quarterfinal"
    SEMIFINAL = "semifinal"
    THIRD_PLACE = "third_place"
    FINAL = "final"

@dataclass
class Game:
    """
    Represents a game between two teams with a game type.
    
    Attributes:
        guild_id: Discord guild id
        team_one_id: Name of the created category
        team_two_id: Discord id of the category created.
        game_type: Game stage
        game_channel_id: Public Discord channel id for setting information
        admin_game_channel_id: Administrative Discord channel id only for captains and Discord guild admin.
        voice_channel_team_one_id: Voice channel used for ingame for team one
        voice_channel_team_two_id: Voice channel used for ingame for team two
        public_game_message_id: Message id where the summary of the game is setted
    """
    id: Optional[int] = None
    guild_id: Optional[int] = None
    team_one_id: Optional[int] = None
    team_two_id: Optional[int] = None
    game_type: GameType
    game_channel_id: int = 0
    admin_game_channel_id: int = 0
    voice_channel_team_one_id: int = 0
    voice_channel_team_two_id: int = 0
    public_game_message_id: int = 0