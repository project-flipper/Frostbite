import datetime
from typing import Annotated
from fastapi import Depends
from frostbite.core.constants.action_type import ActionType
from frostbite.core.socket import send_packet, sio
from frostbite.handlers import get_user_id, packet_handlers
from frostbite.handlers.room import get_current_room
from frostbite.models.action import Action
from frostbite.models.packet import Packet


VOLATILE_TYPES = (
    ActionType.WADDLE,
    ActionType.WAVE,
    ActionType.THROW,
    ActionType.JUMP,
)


@packet_handlers.register("player:action")
async def handle_player_action(
    sid: str,
    packet: Packet[Action],
    user_id: Annotated[int, Depends(get_user_id)],
    room_key: Annotated[str, Depends(get_current_room)],
    namespace: str,
):
    action = Action(
        player_id=user_id,
        type=packet.d.type,
        x=packet.d.x,
        y=packet.d.y,
        to_x=packet.d.to_x,
        to_y=packet.d.to_y,
        since=datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000,
    )

    async with sio.session(sid) as session:
        if packet.d.type == ActionType.WADDLE:
            current_x = packet.d.to_x
            current_y = packet.d.to_y
        elif packet.d.x is not None and packet.d.y is not None:
            current_x = packet.d.x
            current_y = packet.d.y

        if not action.type in VOLATILE_TYPES:
            session["action"] = action

        if current_x is not None and current_y is not None:
            session["x"] = current_x
            session["y"] = current_y

    await send_packet(
        room_key,
        "player:action",
        action,
        namespace=namespace,
    )
