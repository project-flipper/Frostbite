from enum import IntEnum

__all__ = ("ActionType",)


class ActionType(IntEnum):
    IDLE = 0
    WADDLE = 1
    SIT = 2
    WAVE = 3
    DANCE = 4
    THROW = 5
    JUMP = 6
    CJ_BOW = 7
