from dataclasses import dataclass
from typing import Optional

@dataclass
class Channel:
    """
    Represents a created channel in discord.

    Attributes:
        guild_id: Discord guild id
        channel_name: Name of the created channel
        channel_id: Discord id of the channel created.
    """
    id: Optional[int] = None
    guild_id: int = 0
    channel_name: str = ""
    channel_id: int = 0