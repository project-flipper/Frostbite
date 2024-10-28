import jwt
from fastapi import WebSocketException, HTTPException
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from frostbite.core.constants.events import EventEnum
from frostbite.events import _force_fastapi_events_dispatch_as_task, dispatch as global_dispatch
from frostbite.core.constants.close import CloseCode
from frostbite.routes import sio
from frostbite.utils.auth import get_current_user_id, get_oauth_data


async def authenticate(token: str):
    try:
        oauth = get_oauth_data(token, raise_expired=True)
        return get_current_user_id(oauth)
    except ExpiredSignatureError:
        raise WebSocketException(CloseCode.TOKEN_EXPIRED, "Token expired")
    except HTTPException:
        raise WebSocketException(CloseCode.AUTHENTICATION_FAILED, "Authentication failed")

@sio.event
async def connect(sid, environ, auth):
    token = auth.get('token')
    user_id = await authenticate(token)
    # return False # if auth failed, TODO: Check this.

    # save user_id to session
    await sio.save_session(sid, {'user_id': user_id})
    # add user to its own room, so we can broadcast message
    await sio.enter_room(sid, user_id)

    global_dispatch(EventEnum.WORLD_CLIENT_CONNECT, sid)

@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    user_id = session.get('user_id', 'unknown')

    print(f"User {user_id} disconnected")
    global_dispatch(EventEnum.WORLD_CLIENT_DISCONNECT, sid)


# We can make use of sio room, must expand further.
# use SIO event as diff packet types, for example
@sio.event
async def join_room(sid, data):
    # check if user is in any other room, remove then if so
    session = await sio.get_session(sid)
    user_id = session.get('user_id', 'unknown')
    
    room = data.get('room')
    # connect user to the new room
    await sio.enter_room(sid, room)

    # broadcast room join to everyone
    await sio.emit('join_room', {'user': user_id}, room=room)
