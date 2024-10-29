from typing import Any
import socketio
from socketio.exceptions import ConnectionError

from frostbite.core.config import ALLOWED_HOSTS, REDIS_URL
from frostbite.models.packet import Packet

SocketIOAsyncRedisManager = socketio.AsyncRedisManager(REDIS_URL)
SocketIOAsyncServer = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=SocketIOAsyncRedisManager,
    cors_allowed_origins=ALLOWED_HOSTS or "*",  # Configure CORS as needed
)

mgr = SocketIOAsyncRedisManager
sio = SocketIOAsyncServer
__all__ = ["mgr", "sio"]


class SocketException(ConnectionError):
    def __init__(self, code: int, reason: str | None = None) -> None:
        super().__init__(
            f"Connection will disconnect with code {code} and reason {reason}"
        )

        self.code = code
        self.reason = reason


async def send_packet(
    sid_or_room: str, op: str, d: Any, *, skip_sid: str | None = None, namespace: str | None = None
) -> None:
    packet = Packet(op=op, d=d)
    await sio.send(packet.model_dump(), to=sid_or_room, skip_sid=skip_sid, namespace=namespace)


async def send_and_disconnect(
    sid: str, exception: SocketException, *, namespace: str | None = None
) -> None:
    await send_packet(
        sid,
        "error",
        {"code": exception.code, "reason": exception.reason},
        namespace=namespace,
    )
    await sio.disconnect(sid, namespace=namespace)
