from dataclasses import dataclass
from typing import Optional

@dataclass
class GameServer:
    """
    Represents a CS2 server.

    Attributes:
        guild_id: Discord guild id
        ip: IP of the server
        game_port: Port of the game server
        rcon_password: Password for executing rcon
        cstv_port: CSTV port
        is_free: Checks if server is currently in use
    """
    id: Optional[int] = None
    guild_id: int = 0
    ip: str = ""
    game_port: int = 0
    rcon_password: str = ""
    cstv_port: int = 0
    is_free: bool = True
    game_id: int = -1