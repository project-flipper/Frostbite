from pydantic import BaseModel


class Action(BaseModel):
    player_id: int | None = None
    type: int
    x: float | None = None
    y: float | None = None
    to_x: float | None = None
    to_y: float | None = None
    since: float | None = None 
