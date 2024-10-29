import random
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from frostbite.core.socket import send_packet, sio
from frostbite.database.schema.user import UserTable
from frostbite.handlers import get_current_room, get_current_user, get_room_for, packet_handlers
from frostbite.models.action import Action
from frostbite.models.packet import Packet
from frostbite.models.player import Player
from frostbite.models.user import User
from frostbite.models.waddle import Waddle


class RoomJoinData(BaseModel):
    room_id: int | None = None
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


def get_safe_coordinates(room_id: int) -> tuple[float, float]:
    return random.randint(473, 1247), random.randint(704, 734)


async def add_to_room(
    room_key: str,
    sid: str,
    *,
    user: UserTable,
    x: float,
    y: float,
    namespace: str,
) -> None:
    room_id = int(room_key.split(":")[-1])

    player = Player(
        user=await User.from_table(user),
        x=x,
        y=y,
        action=DEFAULT_ACTION,
    )

    await sio.enter_room(sid, room_key, namespace=namespace)

    await send_packet(
        sid,
        "room:join",
        RoomJoinResponse(
            room_id=room_id,
            players=[player],
            waddles=[],
        ),
        namespace=namespace,
    )

    await send_packet(
        room_key,
        "player:add",
        player,
        skip_sid=sid,
        namespace=namespace,
    )


async def remove_from_room(
    room_key: str,
    sid: str,
    *,
    user: UserTable,
    namespace: str,
) -> None:
    player = Player(
        user=await User.from_table(user),
        x=0,
        y=0,
        action=DEFAULT_ACTION,
    )

    await sio.leave_room(sid, room_key, namespace=namespace)
    await send_packet(
        room_key,
        "player:remove",
        player,
        skip_sid=sid,
        namespace=namespace,
    )

@packet_handlers.register("room:join")
async def handle_room_join(
    sid: str,
    packet: Packet[RoomJoinData],
    user: Annotated[UserTable, Depends(get_current_user)],
    namespace: str,
):
    room = get_room_for(sid, namespace=namespace, prefix="rooms:")
    if room is not None:
        await remove_from_room(room, sid, user=user, namespace=namespace)

    room_id = packet.d.room_id if packet.d.room_id is not None else random.choice(SPAWN_ROOMS)
    safe = get_safe_coordinates(room_id)
    x = packet.d.x or safe[0]
    y = packet.d.y or safe[1]

    await add_to_room(f"rooms:{room_id}", sid, user=user, x=x, y=y, namespace=namespace)


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
