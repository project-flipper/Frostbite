import logging

from sqlalchemy.engine.url import URL, make_url
from starlette.config import Config
from starlette.datastructures import CommaSeparatedStrings, Secret

from frostbite.core.logging import InterceptHandler
from frostbite.core.constants.token import JWTTokenType

config = Config(".env")

# API config
API_PREFIX = config("API_PREFIX", cast=str, default="")
API_VERSION = config("API_VERSION", cast=str, default="0.0.1")
API_SUFFIX_VERSION = config("API_SUFFIX_VERSION", cast=bool, default=True)
if API_SUFFIX_VERSION:
    API_PREFIX = f"/{API_PREFIX.strip('/')}/{API_VERSION.strip('/')}"
else:
    API_PREFIX = ""
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=CommaSeparatedStrings, default=[])

# Logging config
DEBUG = config("DEBUG", cast=bool, default=False)
LOGGING_LEVEL = (
    logging.DEBUG
    if DEBUG
    else config("LOGGING_LEVEL", cast=lambda x: getattr(logging, x), default="INFO")
)

# Security config
SECRET_KEY = config("SECRET_KEY", cast=Secret, default="5df9db467ed2c905bcc1")
WORLD_ACCESS_KEY = config(
    "WORLD_ACCESS_KEY", cast=str, default="earlyDevelopmentTesting01"
)
DATABASE_SECRET_KEY = config(
    "DATABASE_SECRET_KEY", cast=Secret, default="change_me1234"
)
ACCESS_TOKEN_EXPIRE_MINUTES = config(
    "ACCESS_TOKEN_EXPIRE_MINUTES", cast=int, default=15 * 60
)  # seconds
DEFAULT_TOKEN_EXPIRE = config("DEFAULT_TOKEN_EXPIRE", cast=int, default=15 * 60)
JWT_ALGORITHM = config(
    "DEFAULT_TOKEN_EXPIRE", cast=JWTTokenType, default=JWTTokenType.HS256
)

# Database config
DB_DRIVER = config("DB_DRIVER", default="postgresql+asyncpg")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = config("DB_PORT", cast=int, default=None)
DB_USER = config("DB_USER", default="postgres")
DB_PASSWORD = config("DB_PASSWORD", cast=Secret, default="password")
DB_DATABASE = config("DB_DATABASE", default="island")
DB_DSN = config(
    "DB_DSN",
    cast=make_url,
    default=URL.create(
        drivername=DB_DRIVER,
        username=DB_USER,
        password=str(DB_PASSWORD),
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE,
    ),
)


# Sentry config
SENTRY_DSN = config("SENTRY_DSN", cast=Secret, default="")

# Redis config
REDIS_HOST = config("REDIS_HOST", cast=str, default="127.0.0.1")
REDIS_PORT = config("REDIS_PORT", cast=int, default=6379)
REDIS_PASSWORD = config("REDIS_PASSWORD", cast=Secret, default=None)
REDIS_SSL_REQUIRED = config("REDIS_SSL_REQUIRED", cast=bool, default=False)
REDIS_SIO_DB = config("REDIS_SIO_DB", cast=int, default=0)

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_SIO_DB}"

# General
FASTAPI_EVENTS_MIDDLEWARE_ID = config(
    "FASTAPI_EVENTS_MIDDLEWARE_ID", cast=int, default=id("fastapi-events")
)
ENVIRONMENT_TYPE = config("ENVIRONMENT_TYPE", cast=str, default="dev")
IS_DEVELOPMENT_MODE = ENVIRONMENT_TYPE == "dev"

# World
WORLD_ID = config("WORLD_ID", cast=int, default=0)
DEFAULT_WORLD_NAMESPACE = config("DEFAULT_WORLD_NAMESPACE", cast=str, default="/")

logging.getLogger().handlers = [InterceptHandler()]
LOGGERS = ("uvicorn.asgi", "uvicorn.access")
for logger_name in LOGGERS:
    logging_logger = logging.getLogger(logger_name)
    logging_logger.setLevel(logging.INFO)
    logging_logger.handlers = [InterceptHandler(level=LOGGING_LEVEL)]
