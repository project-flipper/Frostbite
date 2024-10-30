from enum import Enum


class EventEnum(Enum):
    APP_START_EVENT = "app:start"
    APP_STOP_EVENT = "app:stop"
    # World
    USER_CONNECT = "user:connect"
    USER_AUTH = "user:auth"
    USER_DISCONNECT = "user:disconnect"
    # Rooms
    ROOM_JOIN = "room:join"
    ROOM_LEAVE = "room:leave"
    # Games
    GAME_JOIN = "game:join"
    GAME_START = "game:start"
    GAME_OVER = "game:over"
