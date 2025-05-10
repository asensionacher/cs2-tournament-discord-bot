from dataclasses import dataclass
from typing import Optional

@dataclass
class Summary:
    """
    Summary of tournament summaries
    """
    id: Optional[int] = None
    guild_id: Optional[int] = None
    round_name: Optional[str] = None
    message_id: Optional[int] = None