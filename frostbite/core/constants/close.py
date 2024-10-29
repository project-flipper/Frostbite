from enum import IntEnum


class CloseCode(IntEnum):
    NORMAL = 1000
    INVALID_DATA = 1003
    # Auth
    AUTHENTICATION_FAILED = 4000
    AUTHENTICATION_TIMEOUT = 4001
    TOKEN_EXPIRED = 4002
    # Room
    NOT_IN_ROOM = 4100
    ROOM_FULL = 4101
    ROOM_NOT_FOUND = 4102
    # Game
    GAME_NOT_FOUND = 4200
    GAME_FULL = 4201
    GAME_ALREADY_STARTED = 4202
    GAME_NOT_STARTED = 4203
