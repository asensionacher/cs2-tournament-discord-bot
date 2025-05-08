from dataclasses import dataclass
from typing import Optional

@dataclass
class Summary:
    """
    Summary of tournament summaries
    """
    id: Optional[int] = None
    round: Optional[str] = None
    public_game_message_id: Optional[int] = None