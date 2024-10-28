"""

CLIENT -> Authorization Header  [Verify, //Login//]
       -> event system
           -> Scopes
           -> Priority


scope => single string/Scope, list or tuple or iterable of string/Scope, or callable

@island_event.on(Event(type="PING", scopes=_or(["user:world:auth", "user:world:init"])))
@has_scope()
@allow_once
@disable
async def handle_ping(ctx, *args, **kwargs):
    pass 

"""

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from socketio.exceptions import ConnectionError, ConnectionRefusedError
from loguru import logger

from frostbite.core.constants.close import CloseCode
from frostbite.core.constants.events import EventEnum
from frostbite.handlers import dispatch as dispatch_packet
from frostbite.events import _force_fastapi_events_dispatch_as_task, dispatch as global_dispatch
from frostbite.models.packet import Packet
from frostbite.utils.auth import get_current_user_id, get_oauth_data


async def authenticate(token: str) -> int:
    try:
        oauth = get_oauth_data(token, raise_expired=True)
        return get_current_user_id(oauth)
    except ExpiredSignatureError:
        raise ConnectionRefusedError(CloseCode.TOKEN_EXPIRED, "Token expired")
    except HTTPException:
        raise ConnectionRefusedError(CloseCode.AUTHENTICATION_FAILED, "Authentication failed")


@sio.event
async def connect(sid: str, environ, auth):
    token = auth.get('token')
    user_id = await authenticate(token)

    # save user_id to session
    await sio.save_session(sid, {'user_id': user_id})

    global_dispatch(EventEnum.WORLD_CLIENT_CONNECT, sid)


@sio.on('*', namespace='/world')
async def on_packet(sid: str, event_name: str, data):
    packet = Packet(op=event_name, d=data)
    return dispatch_packet(sid, packet, namespace='/world')


@sio.event
async def disconnect(sid: str):
    session = await sio.get_session(sid)
    user_id = session['user_id']

    logger.info(f"User {user_id} disconnected")
    global_dispatch(EventEnum.WORLD_CLIENT_DISCONNECT, sid)

