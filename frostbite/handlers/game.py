from typing import Annotated
from fastapi import Depends, WebSocket
from pydantic import BaseModel
from frostbite.handlers import get_user_id, packet_handlers, send_packet
from frostbite.models.action import Action
from frostbite.models.packet import Packet


class GameStartData(BaseModel):
    game_id: str


class GameStartResponse(BaseModel):
    game_id: str


@packet_handlers.register("game:start")
async def handle_game_start(
    ws: WebSocket, packet: Packet[GameStartData], user_id: Annotated[int, Depends(get_user_id)]
):
    await send_packet(
        ws,
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
    ws: WebSocket, packet: Packet[GameOverData], user_id: Annotated[int, Depends(get_user_id)]
):
    await send_packet(
        ws,
        "game:over",
        GameOverResponse(
            coins=packet.d.score // 100,
        ),
    )
