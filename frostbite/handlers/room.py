import random

from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event
from loguru import logger
from pydantic import BaseModel

from frostbite.core.config import DEFAULT_WORLD_NAMESPACE
from frostbite.core.constants.events import EventEnum
from frostbite.core.socket import SocketException, SocketErrorEnum, get_sids_in_room, send_packet, sio
from frostbite.database.schema.user import UserTable
from frostbite.events import dispatch
from frostbite.handlers import NamespaceDep, SidDep, get_current_user, packet_handlers
from frostbite.models.action import Action
from frostbite.models.packet import Packet
from frostbite.models.player import Player
from frostbite.models.user import User
from frostbite.models.waddle import Waddle


def get_current_room(
    sid: SidDep,
    *,
    namespace: NamespaceDep = DEFAULT_WORLD_NAMESPACE,
) -> str:
    rooms = sio.manager.get_rooms(sid, namespace)
    if rooms is not None:
        for room in filter(lambda k: k.startswith("rooms:"), rooms):
            return room

    raise SocketException(SocketErrorEnum.NOT_IN_ROOM, "Not in a room")


class RoomJoinData(BaseModel):
    room_id: int | None = None
    x: float | None = None
    y: float | None = None


class RoomJoinResponse(BaseModel):
    room_id: int
    players: list[Player]
    waddles: list[Waddle]



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
    x: float,
    y: float,
    namespace: str,
) -> None:
    room_id = int(room_key.split(":")[-1])

    async with sio.session(sid) as session:
        session['room_id'] = room_id
        session['x'] = x
        session['y'] = y
        session['action'] = DEFAULT_ACTION

    await sio.enter_room(sid, room_key, namespace=namespace)
    dispatch(EventEnum.ROOM_JOIN, sid, room_key, namespace)


async def remove_from_room(
    room_key: str,
    sid: str,
    *,
    namespace: str,
) -> None:
    await sio.leave_room(sid, room_key, namespace=namespace)
    dispatch(EventEnum.ROOM_LEAVE, sid, room_key, namespace)

@packet_handlers.register("room:join")
async def handle_room_join(
    sid: str,
    packet: Packet[RoomJoinData],
    namespace: str,
):
    try:
        room = get_current_room(sid, namespace=namespace)
        await remove_from_room(room, sid, namespace=namespace)
    except SocketException:
        pass

    room_id = packet.d.room_id if packet.d.room_id is not None else random.choice(SPAWN_ROOMS)
    safe = get_safe_coordinates(room_id)
    x = packet.d.x or safe[0]
    y = packet.d.y or safe[1]

    await add_to_room(f"rooms:{room_id}", sid, x=x, y=y, namespace=namespace)


@local_handler.register(event_name=str(EventEnum.ROOM_JOIN))
async def on_room_join(event: Event) -> None:
    _, (sid, room_key, namespace) = event
    logger.info(f'User {sid} joined {room_key} on {namespace}')

    session = await sio.get_session(sid)
    player = Player(
        user=await User.from_table(await get_current_user(session['user_id'])),
        x=session['x'],
        y=session['y'],
        action=session['action'],
    )

    players = [player]
    for other_sid in get_sids_in_room(room_key, namespace):
        if other_sid == sid:
            continue

        other_session = await sio.get_session(other_sid)
        user = await UserTable.query_by_id(other_session['user_id'])

        if not user:
            continue

        other_player = Player(
            user=await User.from_table(user),
            x=other_session['x'],
            y=other_session['y'],
            action=other_session['action'],
        )
        players.append(other_player)

    await send_packet(
        sid,
        "room:join",
        RoomJoinResponse(
            room_id=int(room_key.split(":")[-1]),
            players=players,
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

@local_handler.register(event_name=str(EventEnum.ROOM_LEAVE))
async def on_room_leave(event: Event) -> None:
    _, (sid, room_key, namespace) = event
    logger.info(f'User {sid} left {room_key} on {namespace}')

    session = await sio.get_session(sid)
    user = await UserTable.query_by_id(session['user_id'])

    if not user:
        return

    player = Player(
        user=await User.from_table(user),
        x=0,
        y=0,
        action=DEFAULT_ACTION,
    )

    await send_packet(
        room_key,
        "player:remove",
        player,
        skip_sid=sid,
        namespace=namespace,
    )


@local_handler.register(event_name=str(EventEnum.USER_DISCONNECT))
async def on_user_disconnect(event: Event) -> None:
    _, (sid, session, rooms) = event

    user = await UserTable.query_by_id(session['user_id'])
    if rooms is not None and user:
        for room_key in filter(lambda k: k.startswith("rooms:"), rooms):
            player = Player(
                user=await User.from_table(user),
                x=0,
                y=0,
                action=DEFAULT_ACTION,
            )

            await send_packet(
                room_key,
                "player:remove",
                player,
                skip_sid=sid,
                namespace=DEFAULT_WORLD_NAMESPACE,
            )

    logger.info(f'Disconnected user {sid} ({session}) with rooms {rooms}')
