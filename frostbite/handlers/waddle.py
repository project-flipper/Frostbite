from typing import Annotated
from fastapi import Depends
from pydantic import BaseModel

from frostbite.core.socket import send_packet
from frostbite.database.schema.user import UserTable
from frostbite.handlers import get_current_user, packet_handlers
from frostbite.handlers.room import get_current_room
from frostbite.models.packet import Packet


class WaddleJoinData(BaseModel):
    waddle_id: int


class WaddleJoinResponse(BaseModel):
    waddle_id: int
    player: int


class WaddleLeaveData(BaseModel):
    waddle_id: int


class WaddleLeaveResponse(BaseModel):
    waddle_id: int
    player: int

@packet_handlers.register("waddle:join")
async def handle_waddle_join(
    packet: Packet[WaddleJoinData],
    user: Annotated[UserTable, Depends(get_current_user)],
    room_key: Annotated[str, Depends(get_current_room)],
    namespace: str,
):
    await send_packet(
        room_key,
        "waddle:join",
        WaddleJoinResponse(
            waddle_id=packet.d.waddle_id,
            player=user.id,
        ),
        namespace=namespace,
    )


@packet_handlers.register("waddle:leave")
async def handle_waddle_leave(
    packet: Packet[WaddleLeaveData],
    user: Annotated[UserTable, Depends(get_current_user)],
    room_key: Annotated[str, Depends(get_current_room)],
    namespace: str,
):
    await send_packet(
        room_key,
        "waddle:leave",
        WaddleLeaveResponse(
            waddle_id=packet.d.waddle_id,
            player=user.id,
        ),
        namespace=namespace,
    )
