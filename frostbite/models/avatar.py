from __future__ import annotations

from pydantic import BaseModel

from frostbite.database.schema.avatar import AvatarTable


class Avatar(BaseModel):
    color: int
    head: int
    face: int
    neck: int
    body: int
    hand: int
    feet: int
    photo: int
    flag: int
    transformation: str | None

    @classmethod
    async def from_table(cls, avatar: AvatarTable) -> "Avatar":
        return cls(
            color=avatar.color,
            head=avatar.head,
            face=avatar.face,
            neck=avatar.neck,
            body=avatar.body,
            hand=avatar.hand,
            feet=avatar.feet,
            photo=avatar.photo,
            flag=avatar.flag,
            transformation=avatar.transformation,
        )
