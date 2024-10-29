from typing import Annotated
from fastapi import Depends
from pydantic import BaseModel
from frostbite.handlers import get_user_id, packet_handlers, send_packet
from frostbite.models.packet import Packet


class GameStartData(BaseModel):
    game_id: str


class GameStartResponse(BaseModel):
    game_id: str


@packet_handlers.register("game:start")
async def handle_game_start(
    sid: str, packet: Packet[GameStartData]
):
    await send_packet(
        sid,
        "game:start",
        GameStartResponse(
            game_id=packet.d.game_id,
        ),
    )

class GameOverData(BaseModel):
    score: int


class GameOverResponse(BaseModel):
    coins: int

@packet_handlers.register("game:over")
async def handle_game_over(
    sid: str, packet: Packet[GameOverData]
):
    await send_packet(
        sid,
        "game:over",
        GameOverResponse(
            coins=packet.d.score // 10,
        ),
    )
