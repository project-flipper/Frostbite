from frostbite.core.config import WORLD_ID
from frostbite.entities import Entity


class BaseWorldEntity(Entity):
    __prefix__ = f"worlds.{WORLD_ID}"


class WorldEntity(BaseWorldEntity):
    pass
