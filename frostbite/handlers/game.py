from pydantic import BaseModel
from frostbite.core.socket import send_packet
from frostbite.handlers import packet_handlers
from frostbite.models.packet import Packet


class GameStartData(BaseModel):
    game_id: str


class GameStartResponse(BaseModel):
    game_id: str


@packet_handlers.register("game:start")
async def handle_game_start(
    sid: str,
    packet: Packet[GameStartData],
    namespace: str,
):
    await send_packet(
        sid,
        "game:start",
        GameStartResponse(
            game_id=packet.d.game_id,
        ),
        namespace=namespace,
    )


class GameOverData(BaseModel):
    score: int


class GameOverResponse(BaseModel):
    coins: int


@packet_handlers.register("game:over")
async def handle_game_over(
    sid: str,
    packet: Packet[GameOverData],
    namespace: str,
):
    await send_packet(
        sid,
        "game:over",
        GameOverResponse(
            coins=packet.d.score // 10,
        ),
        namespace=namespace,
    )
