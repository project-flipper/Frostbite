from enum import StrEnum
from typing import Annotated, Literal
from fastapi import Depends
from pydantic import BaseModel
from frostbite.core.socket import send_packet
from frostbite.handlers import get_user_id, packet_handlers
from frostbite.handlers.room import get_current_room
from frostbite.models.packet import Packet


class MessageType(StrEnum):
    TEXT = "TEXT"
    EMOJI = "EMOJI"
    JOKE = "JOKE"
    TOUR = "TOUR"


class TextMessageData(BaseModel):
    type: Literal[MessageType.TEXT]
    message: str


class EmojiMessageData(BaseModel):
    type: Literal[MessageType.EMOJI]
    emoji: int


class JokeMessageData(BaseModel):
    type: Literal[MessageType.JOKE]
    joke: int


class TourMessageData(BaseModel):
    type: Literal[MessageType.TOUR]


class MessageCreateResponse(BaseModel):
    type: MessageType
    player_id: int
    message: str | None = None
    emoji: int | None = None
    joke: int | None = None
    banned: bool = False


@packet_handlers.register("message:create")
async def handle_message_create(
    packet: Packet[
        TextMessageData | EmojiMessageData | JokeMessageData | TourMessageData
    ],
    user_id: Annotated[int, Depends(get_user_id)],
    room_key: Annotated[str, Depends(get_current_room)],
    namespace: str,
):
    if packet.d.type == MessageType.TEXT:
        data = MessageCreateResponse(player_id=user_id, type=packet.d.type, message=packet.d.message, banned=False)  # type: ignore
    elif packet.d.type == MessageType.EMOJI:
        data = MessageCreateResponse(player_id=user_id, type=packet.d.type, emoji=packet.d.emoji, banned=False)  # type: ignore
    elif packet.d.type == MessageType.JOKE:
        data = MessageCreateResponse(player_id=user_id, type=packet.d.type, joke=packet.d.joke, banned=False)  # type: ignore
    elif packet.d.type == MessageType.TOUR:
        data = MessageCreateResponse(
            player_id=user_id, type=packet.d.type, banned=False
        )

    await send_packet(room_key, "message:create", data, namespace=namespace)
