from typing import Annotated
from fastapi import Depends
from frostbite.core.socket import send_packet, sio
from frostbite.handlers import get_user_id, packet_handlers
from frostbite.handlers.room import get_current_room
from frostbite.models.action import Action
from frostbite.models.packet import Packet


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
        frame=packet.d.frame,
        x=packet.d.x,
        y=packet.d.y,
    )

    async with sio.session(sid) as session:
        if 8 <= action.frame <= 15:
            session["x"] = packet.d.x
            session["y"] = packet.d.y
        if not 26 <= action.frame <= 37:
            session["action"] = action

    await send_packet(
        room_key,
        "player:action",
        action,
        namespace=namespace,
    )
