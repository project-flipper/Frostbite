import socketio

from frostbite.core.config import REDIS_URL, ALLOWED_HOSTS

SocketIOAsyncRedisManager = socketio.AsyncRedisManager(REDIS_URL)
SocketIOAsyncServer = socketio.AsyncServer(
    async_mode='asgi',
    client_manager=SocketIOAsyncRedisManager,
    cors_allowed_origins=ALLOWED_HOSTS or ["http://localhost"]  # Configure CORS as needed
)

mgr = SocketIOAsyncRedisManager
sio = SocketIOAsyncServer
__all__ = ["mgr", "sio"]

