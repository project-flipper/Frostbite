from pydantic import BaseModel

from frostbite.database import ASYNC_SESSION
from frostbite.database.schema.user import UserTable
from frostbite.models.avatar import Avatar
from frostbite.models.presence import Presence
from frostbite.models.relationship import Relationship
from frostbite.models.membership import Membership


class BaseUser(BaseModel):
    id: int
    username: str
    nickname: str
    avatar: Avatar
    member: Membership | None
    igloo_id: int | None
    mascot_id: int | None


class User(BaseUser):
    relationship: Relationship | None
    public_stampbook: bool
    presence: Presence | None

    @classmethod
    async def from_table(cls, user: UserTable) -> "User":
        return cls(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=Avatar.model_validate(user.avatar, from_attributes=True),
            member=None,
            igloo_id=0,
            mascot_id=None,
            relationship=None,
            public_stampbook=False,
            presence=None,
        )


class MyUser(BaseUser):
    igloo_id: int
    is_moderator: bool
    is_stealth: bool

    @classmethod
    async def from_table(cls, user: UserTable) -> "MyUser":
        return cls(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=Avatar.model_validate(user.avatar, from_attributes=True),
            member=None,
            igloo_id=0,
            mascot_id=None,
            is_moderator=True,
            is_stealth=False,
        )
