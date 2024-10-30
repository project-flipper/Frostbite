from __future__ import annotations

import asyncio
import functools
import inspect
from contextlib import AsyncExitStack
from contextvars import ContextVar
from typing import Annotated, Any, Callable

from fastapi import Depends, HTTPException
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant, get_parameterless_sub_dependant
from fastapi.params import Depends as ParamDepends
from jwt import ExpiredSignatureError
from loguru import logger
from pydantic import ValidationError
from socketio.exceptions import ConnectionRefusedError

from frostbite.core.config import DEFAULT_WORLD_NAMESPACE
from frostbite.core.constants.close import CloseCode
from frostbite.core.constants.events import EventEnum
from frostbite.core.socket import (
    SocketCriticalException,
    SocketException,
    send_and_disconnect,
    send_error,
    sio,
)
from frostbite.database.schema.user import UserTable
from frostbite.events import dispatch as global_dispatch
from frostbite.models.packet import Packet
from frostbite.utils.auth import get_current_user_id, get_oauth_data
from frostbite.utils.dependencies import solve_dependencies

__all__ = (
    "packet_handlers",
    "get_event",
    "get_session",
    "get_user_id",
    "get_current_user",
    "get_sid",
    "get_packet",
    "get_namespace",
    "get_custom_packet",
    "PacketHandler",
    "SessionDep",
    "SidDep",
    "PacketDep",
    "NamespaceDep",
)

type Event = tuple[str, Packet, str]
_event: ContextVar[Event] = ContextVar("sid")


class DelayedInjection:
    def __init__(self, _cb: Callable[[inspect.Parameter], Any]) -> None:
        self._callback = _cb

    def __call__(self, param) -> Any:
        return self._callback(param)


class PacketHandler:
    def __init__(self):
        self._registry: dict[str, dict[str, Callable]] = {}

    def register(
        self,
        op: str = "*",
        func: Callable | None = None,
        *,
        dependencies: list[ParamDepends] | None = None,
        namespace: str = DEFAULT_WORLD_NAMESPACE,
    ):
        """Register a handler for the given packet.

        Usage:
            from frostbite.handlers import packet_handlers
            from frostbite.models.packet import Packet

            @packet_handlers.register("my:event") # Register a handler as a decorator
            async def handle_my_event(sid: string, packet: Packet):
                print(f"Received event {packet.op} with payload {packet.d}")

        Args:
            :param op: The operation to be associated with the handler. Use "*", the default value, to match all packets.
            :param func: The function to be registered as a handler.  Typically, you would use `register` as a decorator and omit this argument.
            :param dependencies: A list of dependencies to include within the handler.
            :param namespace: The namespace to register this handler under. Defaults to the default world namespace.
        """

        def wrapped(_func):
            self._register_handler(op, _func, dependencies, namespace=namespace)
            return _func

        if func is None:
            return wrapped

        return wrapped(func)

    def unregister(
        self, op: str, func: Callable, *, namespace: str = DEFAULT_WORLD_NAMESPACE
    ) -> None:
        """Unregisters a packet handler.

        Args:
            :param op: The operation to be associated with the handler. Use "*", the default value, to match all packets.
            :param func: The function to be registered as a handler.  Typically, you would use `register` as a decorator and omit this argument.
        """
        self._unregister_handler(op, func, namespace=namespace)

    async def handle(
        self, sid: str, packet: Packet, *, namespace: str = DEFAULT_WORLD_NAMESPACE
    ) -> None:
        _event.set((sid, packet, namespace))

        handler = self._get_handler_for_event(event_name=packet.op, namespace=namespace)

        if handler is None:
            logger.warning(f"No handler found for {packet.op}")
            return

        async with AsyncExitStack() as cm:
            # resolve dependencies
            dependant: Dependant = getattr(handler, "__dependant__")

            if not dependant.call:
                return

            try:
                # TODO: mock request object? or access an internal API to fetch it
                solved = await solve_dependencies(
                    dependant=dependant, async_exit_stack=cm
                )

                if inspect.iscoroutinefunction(dependant.call):
                    await dependant.call(**solved.values)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, functools.partial(dependant.call, **solved.values)
                    )
            except ValidationError as e:
                logger.opt(exception=e).error(e)
                await send_and_disconnect(
                    sid,
                    SocketCriticalException(
                        CloseCode.INVALID_DATA, "Invalid data received"
                    ),
                    namespace=namespace,
                )
            except SocketCriticalException as e:
                await send_and_disconnect(sid, e, namespace=namespace)
            except SocketException as e:
                await send_error(sid, e, namespace=namespace)
            except Exception as e:
                logger.opt(exception=e).error(
                    "An error occurred when dispatching a packet"
                )

    def _register_handler(
        self,
        event_name: str,
        func: Callable,
        dependencies: list[ParamDepends] | None = None,
        *,
        namespace: str = DEFAULT_WORLD_NAMESPACE,
    ):
        if not isinstance(event_name, str):
            event_name = str(event_name)

        if namespace not in self._registry:
            self._registry[namespace] = {}

        handlers = self._registry[namespace]

        if event_name in handlers and event_name != "*":
            logger.warning(f"Overwriting handler for {event_name}")

        path_format = f"packet:{event_name}"

        self._inject_params(func)

        dependant = get_dependant(path=path_format, call=func)
        dependencies = list(dependencies or [])
        for depends in dependencies[::-1]:
            dependant.dependencies.insert(
                0,
                get_parameterless_sub_dependant(depends=depends, path=path_format),
            )
        setattr(func, "__dependant__", dependant)

        handlers[event_name] = func

    def _get_injection_params(self) -> dict[Any, Any]:
        return {
            "sid": SidDep,
            Packet: PacketDep,
            "packet": DelayedInjection(
                lambda p: Annotated[
                    p.annotation, Depends(get_custom_packet(p.annotation))
                ]
            ),
            "namespace": NamespaceDep,
            "session": SessionDep,
        }

    def _inject_params(self, func: Callable) -> None:
        sig = inspect.signature(func)
        _injections = self._get_injection_params()

        params = []
        for param in sig.parameters.values():
            to_inject = None

            if param.annotation in _injections:
                to_inject = _injections[param.annotation]
            elif param.name in _injections:
                to_inject = _injections[param.name]

            if to_inject is not None:
                if isinstance(to_inject, DelayedInjection):
                    to_inject = to_inject(param)
                param = param.replace(annotation=to_inject)

            params.append(param)

        sig = sig.replace(parameters=params)

        if inspect.ismethod(func):
            func.__func__.__signature__ = sig
        else:
            func.__signature__ = sig

    def _get_handler_for_event(
        self, event_name, *, namespace: str = DEFAULT_WORLD_NAMESPACE
    ) -> Callable | None:
        if not isinstance(event_name, str):
            event_name = str(event_name)

        if namespace not in self._registry:
            self._registry[namespace] = {}

        handlers = self._registry[namespace]

        return handlers.get(event_name)

    def _unregister_handler(
        self, event_name, func, *, namespace: str = DEFAULT_WORLD_NAMESPACE
    ):
        if not isinstance(event_name, str):
            event_name = str(event_name)

        if namespace not in self._registry:
            return

        handlers = self._registry[namespace]

        if event_name not in handlers:
            return

        del handlers[event_name]

        if len(handlers) == 0:
            del self._registry[namespace]


async def get_session(namespace: str = DEFAULT_WORLD_NAMESPACE) -> dict[str, Any]:
    sid = _event.get()[0]
    return await sio.get_session(sid, namespace=namespace)


SessionDep = Annotated[dict[str, Any], Depends(get_session)]


def get_user_id(session: Annotated[dict[str, Any], Depends(get_session)]) -> int:
    return session["user_id"]


async def get_current_user(user_id: Annotated[int, Depends(get_user_id)]) -> UserTable:
    user = await UserTable.query_by_id(user_id)

    if user is None or user.id != user_id:
        raise SocketCriticalException(
            CloseCode.AUTHENTICATION_FAILED, "Authentication failed"
        )

    return user


def get_event() -> Event:
    return _event.get()


def get_sid(event: Annotated[Event, Depends(get_event)]) -> str:
    return event[0]


SidDep = Annotated[str, Depends(get_sid)]


def get_packet(event: Annotated[Event, Depends(get_event)]) -> Packet:
    return event[1]


PacketDep = Annotated[Packet, Depends(get_packet)]


def get_namespace(event: Annotated[Event, Depends(get_event)]) -> str:
    return event[2]


NamespaceDep = Annotated[str, Depends(get_namespace)]


def get_custom_packet(cls=Packet):
    def _wrap(p: PacketDep) -> Packet:
        return cls.model_validate(p.model_dump())

    return _wrap


packet_handlers = PacketHandler()


async def authenticate(token: str) -> int:
    try:
        oauth = get_oauth_data(token, raise_expired=True)
        return get_current_user_id(oauth)
    except ExpiredSignatureError:
        raise ConnectionRefusedError(CloseCode.TOKEN_EXPIRED, "Token expired")
    except HTTPException:
        raise ConnectionRefusedError(
            CloseCode.AUTHENTICATION_FAILED, "Authentication failed"
        )


@sio.event
async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any]) -> bool:
    global_dispatch(EventEnum.USER_CONNECT, sid)

    token = auth.get("token")
    if not token:
        return False

    user_id = await authenticate(token)
    logger.info(f"User {user_id} connected")

    try:
        # save user_id to session
        await sio.save_session(sid, {"user_id": user_id})
    except KeyError:
        # probably disconnected? ignore
        logger.error(f"User {user_id} disconnected before session could be saved")
        return False

    global_dispatch(EventEnum.USER_AUTH, sid)

    return True


@sio.event(namespace=DEFAULT_WORLD_NAMESPACE)
async def message(sid: str, event_name: str, data: Any) -> None:
    packet = Packet(op=event_name, d=data)
    logger.info(f"Dispatching packet for {packet.op} with data {packet.d}")
    await packet_handlers.handle(sid, packet, namespace=DEFAULT_WORLD_NAMESPACE)


@sio.event
async def disconnect(sid: str) -> None:
    session = await sio.get_session(sid)
    user_id = session["user_id"]

    logger.info(f"User {user_id} disconnected {sio.rooms(sid)}")
    global_dispatch(EventEnum.USER_DISCONNECT, sid)
