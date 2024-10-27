import random
from typing import Annotated, Any
from fastapi import Depends, WebSocket
from pydantic import BaseModel
from frostbite.database.schema.user import UserTable
from frostbite.handlers import packet_handlers, send_packet, get_current_user
from frostbite.models.action import Action
from frostbite.models.packet import Packet
from frostbite.models.player import Player
from frostbite.models.user import User
from frostbite.models.waddle import Waddle


class RoomJoinData(BaseModel):
    room_id: int
    x: float | None = None
    y: float | None = None


class RoomJoinResponse(BaseModel):
    room_id: int
    players: list[Player]
    waddles: list[Waddle]


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


DEFAULT_ACTION = Action(frame=0)
SPAWN_ROOMS = [
    100,  # town
    200,  # village
    230,  # mtn
    300,  # plaza
    400,  # beach
    800,  # dock
    801,  # forts
    802,  # rink
    805,  # berg
    807,  # shack
    809,  # forest
    810,  # cove
]  # TODO: get from crumbs instead and verify if full


async def send_packet_to_room(room_id: int, op: str, d: Any):
    pass

def get_safe_coordinates(room_id: int) -> tuple[float, float]:
    return random.randint(473, 1247), random.randint(704, 734)


@packet_handlers.register("room:join")
async def handle_room_join(
    ws: WebSocket,
    packet: Packet[RoomJoinData],
    user: Annotated[UserTable, Depends(get_current_user)],
):
    safe = get_safe_coordinates(packet.d.room_id)
    x = packet.d.x or safe[0]
    y = packet.d.y or safe[1]

    await send_packet(
        ws,
        "room:join",
        RoomJoinResponse(
            room_id=packet.d.room_id,
            players=[
                Player(
                    user=await User.from_table(user),
                    x=x,
                    y=y,
                    action=DEFAULT_ACTION,
                )
            ],
            waddles=[],
        ),
    )


@packet_handlers.register("room:spawn")
async def handle_room_spawn(
    ws: WebSocket, packet: Packet, user: Annotated[UserTable, Depends(get_current_user)]
):
    room_id = random.choice(SPAWN_ROOMS)
    # TODO: get available rooms and dispatch a room:join with a safe x, y from crumbs
    safe = get_safe_coordinates(room_id)

    await send_packet(
        ws,
        "room:join",
        RoomJoinResponse(
            room_id=room_id,
            players=[
                Player(
                    user=await User.from_table(user),
                    x=safe[0],
                    y=safe[1],
                    action=DEFAULT_ACTION,
                )
            ],
            waddles=[],
        ),
    )

@packet_handlers.register("waddle:join")
async def handle_waddle_join(
    ws: WebSocket, packet: Packet[WaddleJoinData], user: Annotated[UserTable, Depends(get_current_user)]
):
    await send_packet(
        ws,
        "waddle:join",
        WaddleJoinResponse(
            waddle_id=packet.d.waddle_id,
            player=user.id,
        ),
    )

@packet_handlers.register("waddle:leave")
async def handle_waddle_leave(
    ws: WebSocket, packet: Packet[WaddleLeaveData], user: Annotated[UserTable, Depends(get_current_user)]
):
    await send_packet(ws,
        "waddle:leave",
        WaddleLeaveResponse(
            waddle_id=packet.d.waddle_id,
            player=user.id,
        )
    )
