from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerRole:
    """
    Represents a Discord server role for storing the role name
    """
    id: Optional[int] = None
    guild_id: Optional[int] = None
    role_name: str = ""
    role_id: Optional[int] = None