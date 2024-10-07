from pydantic import BaseModel

from frostbite.models.action import Action
from frostbite.models.user import MyUser, User


class Player(BaseModel):
    user: User | MyUser
    x: float
    y: float
    action: Action
