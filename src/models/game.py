from dataclasses import dataclass
from typing import Optional
from enum import Enum
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
    # Required fields first
    
    # Optional fields with defaults
    id: Optional[int] = None
    guild_id: Optional[int] = None
    team_one_id: Optional[int] = None
    team_two_id: Optional[int] = None
    team_winner: Optional[int] = None
    game_type: Optional[str] = None
    game_channel_id: Optional[int] = None
    admin_game_channel_id: Optional[int] = None
    voice_channel_team_one_id: Optional[int] = None
    voice_channel_team_two_id: Optional[int] = None
    public_game_message_id: Optional[int] = None