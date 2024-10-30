from enum import IntEnum
from typing import Any, Generator, cast

import socketio

from frostbite.core.config import ALLOWED_HOSTS, REDIS_URL
from frostbite.models.packet import Packet

__all__ = (
    "mgr",
    "sio",
    "SocketException",
    "SocketCriticalException",
    "SocketErrorEnum",
    "send_packet",
    "send_error",
    "send_and_disconnect",
    "get_sids_in_room",
)

SocketIOAsyncRedisManager = socketio.AsyncRedisManager(REDIS_URL.render_as_string(False))
SocketIOAsyncServer = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=SocketIOAsyncRedisManager,
    cors_allowed_origins=ALLOWED_HOSTS or "*",  # Configure CORS as needed
)

mgr = SocketIOAsyncRedisManager
sio = SocketIOAsyncServer


class SocketException(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class SocketCriticalException(SocketException):
    pass


class SocketErrorEnum(IntEnum):
    # Room
    NOT_IN_ROOM = 4100
    ROOM_FULL = 4101
    ROOM_NOT_FOUND = 4102
    # Game
    GAME_NOT_FOUND = 4200
    GAME_FULL = 4201
    GAME_ALREADY_STARTED = 4202
    GAME_NOT_STARTED = 4203


async def send_packet(
    sid_or_room: str,
    op: str,
    d: Any,
    *,
    skip_sid: str | None = None,
    namespace: str | None = None,
) -> None:
    packet = Packet(op=op, d=d)
    await sio.send(
        packet.model_dump(), to=sid_or_room, skip_sid=skip_sid, namespace=namespace
    )


async def send_error(
    sid: str, error: SocketException, *, namespace: str | None = None
) -> None:
    await send_packet(
        sid,
        "error",
        {"code": error.code, "message": error.message},
        namespace=namespace,
    )


async def send_and_disconnect(
    sid: str, error: SocketException, *, namespace: str | None = None
) -> None:
    await send_packet(
        sid,
        "error",
        {"code": error.code, "message": error.message},
        namespace=namespace,
    )
    await sio.disconnect(sid, namespace=namespace)


def get_sids_in_room(room: str, namespace: str) -> Generator[str, None, None]:
    for sid, _ in sio.manager.get_participants(namespace, room):
        try:
            if sio.manager.is_connected(sid, namespace):
                yield cast(str, sid)
        except KeyError:
            pass
