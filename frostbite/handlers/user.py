from typing import Annotated
from fastapi import Depends
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import update

from frostbite.core.socket import SocketException, send_packet
from frostbite.database import ASYNC_SESSION
from frostbite.database.schema.avatar import AvatarTable
from frostbite.database.schema.user import UserTable
from frostbite.handlers import get_current_user, packet_handlers
from frostbite.handlers.room import get_current_room
from frostbite.models.avatar import Avatar
from frostbite.models.packet import Packet
from frostbite.models.user import MyUser, User


class AvatarMask(BaseModel):
    color: int | None = None
    head: int | None = None
    face: int | None = None
    neck: int | None = None
    body: int | None = None
    hand: int | None = None
    feet: int | None = None
    flag: int | None = None
    photo: int | None = None


@packet_handlers.register("player:avatar")
async def handle_player_action(
    sid: str,
    packet: Packet[AvatarMask],
    user: Annotated[UserTable, Depends(get_current_user)],
    namespace: str,
) -> None:
    current_avatar = (await Avatar.from_table(user.avatar)).model_dump()
    new_avatar = packet.d.model_dump()

    has_changed = False

    fields: dict[str, int] = {}
    for field, value in new_avatar.items():
        if value is not None:
            fields[field] = value
            if not has_changed:
                has_changed = fields[field] != current_avatar[field]

    if not has_changed:
        logger.info(f"Avatar has not changed\n{current_avatar}\n{new_avatar}")
        return

    async with ASYNC_SESSION() as session:
        await session.execute(
            update(AvatarTable).values(fields).where(AvatarTable.id == user.avatar.id)
        )
        await session.commit()

    try:
        room = get_current_room(sid, namespace=namespace)

        current_user = await UserTable.query_by_id(user.id)
        if current_user is None:
            logger.error("User not found", user.id)
            return

        await send_packet(
            sid,
            "user:update",
            await MyUser.from_table(current_user),
            namespace=namespace,
        )
        await send_packet(
            room,
            "user:update",
            await User.from_table(current_user),
            skip_sid=sid,
            namespace=namespace,
        )
    except SocketException:
        logger.error("User not in room", sid)
        return
