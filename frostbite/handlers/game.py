from typing import Annotated
from fastapi import Depends
from pydantic import BaseModel
from frostbite.core.config import DEFAULT_WORLD_NAMESPACE
from frostbite.core.socket import SocketErrorEnum, SocketException, send_packet, sio
from frostbite.handlers import NamespaceDep, SidDep, packet_handlers
from frostbite.handlers.room import get_current_room, remove_from_room
from frostbite.models.packet import Packet


def get_current_game(
    sid: SidDep,
    *,
    namespace: NamespaceDep = DEFAULT_WORLD_NAMESPACE,
) -> str:
    rooms = sio.manager.get_rooms(sid, namespace)
    if rooms is not None:
        for room in filter(lambda k: k.startswith("games:"), rooms):
            return room

    raise SocketException(SocketErrorEnum.GAME_NOT_STARTED, "Not in a game")


class GameStartData(BaseModel):
    game_id: str


class GameStartResponse(BaseModel):
    game_id: str


async def add_to_game(game_key: str, sid: str, *, namespace: str) -> None:
    game_id = game_key.split(":")[1]

    await send_packet(
        game_key,
        "game:start",
        GameStartResponse(
            game_id=game_id,
        ),
        namespace=namespace,
    )

    await sio.enter_room(sid, game_key, namespace=namespace)


@packet_handlers.register("game:start")
async def handle_game_start(
    sid: str,
    packet: Packet[GameStartData],
    namespace: str,
):
    try:
        room = get_current_room(sid, namespace=namespace)
        await remove_from_room(room, sid, namespace=namespace)
    except SocketException:
        pass

    game_key = f"games:{packet.d.game_id}"
    await add_to_game(game_key, sid, namespace=namespace)


class GameOverData(BaseModel):
    score: int


class GameOverResponse(BaseModel):
    coins: int


@packet_handlers.register("game:over")
async def handle_game_over(
    sid: str,
    packet: Packet[GameOverData],
    game_key: Annotated[str, Depends(get_current_game)],
    namespace: str,
):
    await send_packet(
        game_key,
        "game:over",
        GameOverResponse(
            coins=packet.d.score // 10,
        ),
        namespace=namespace,
    )
