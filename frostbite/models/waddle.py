from pydantic import BaseModel


class Waddle(BaseModel):
    waddle_id: int
    players: list[int]
