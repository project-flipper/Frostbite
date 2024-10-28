import sys

import sentry_sdk
import socketio
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi_events.handlers.local import local_handler
from fastapi_events.middleware import EventHandlerASGIMiddleware
from loguru import logger
from pydantic import ValidationError
from sentry_sdk.integrations.loguru import LoguruIntegration
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp
from starlette_context.middleware import RawContextMiddleware

import frostbite.database.schema as _
import frostbite.routes
from frostbite import events, handlers
from frostbite.core.config import (
    ALLOWED_HOSTS,
    API_PREFIX,
    API_VERSION,
    DEBUG,
    FASTAPI_EVENTS_MIDDLEWARE_ID,
    WORLD_ID,
    SENTRY_DSN,
    WORLD_PACKETS_MIDDLEWARE_ID,
)
from frostbite.core.socket import sio
from frostbite.core.error.http_error import http_error_handler
from frostbite.core.error.validation_error import http422_error_handler
from frostbite.core.lifespan import manage_app_lifespan
from frostbite.utils.routes import get_modules

print(
    r"""



___________                      __ ___.   .__  __          
\_   _____/______  ____  _______/  |\_ |__ |__|/  |_  ____  
 |    __) \_  __ \/  _ \/  ___/\   __\ __ \|  \   __\/ __ \ 
 |     \   |  | \(  <_> )___ \  |  | | \_\ \  ||  | \  ___/ 
 \___  /   |__|   \____/____  > |__| |___  /__||__|  \___  >
     \/                     \/           \/              \/ 

"""
)


def catch_exceptions():
    sys.excepthook = lambda _type, message, stack: (
        logger.opt(exception=(_type, message, stack)).error("Uncaught Exception")
        if not issubclass(_type, (ValidationError, RequestValidationError))
        else logger.error("Validation error occured")
    )


def initialize_sentry():
    sentry_sdk.init(
        dsn=str(SENTRY_DSN),
        traces_sample_rate=1.0,  # 1.0 => 100% capture rate
        integrations=[LoguruIntegration()],
    )


def get_application() -> ASGIApp:
    catch_exceptions()
    initialize_sentry()

    logger.info("Running Frostbite in WS endpoint mode")
    logger.info(f"Frostbite World ID {WORLD_ID}")

    logger.debug("docs_url: {}", f"{API_PREFIX}/docs")
    logger.debug("redoc_url: {}", f"{API_PREFIX}/redocs")
    application = FastAPI(
        debug=DEBUG,
        title="Frostbite Server",
        description="WS endpoint for ClubPenguin HTML5 client",
        version=API_VERSION,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redocs",
        lifespan=manage_app_lifespan,
    )

    _prefix = f"{API_PREFIX}"

    logger.info(f"Frostbite version {API_VERSION}")
    logger.info(f"Frostbite API endpoint prefix {_prefix}")
    logger.info("Frostbite setting up")

    logger.info("Frostbite adding middlewares")

    logger.debug("Frostbite adding CORS Middleware")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_HOSTS or ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    logger.debug("Frostbite adding Event Handler ASGI Middleware")
    application.add_middleware(
        EventHandlerASGIMiddleware,
        handlers=[local_handler],
        middleware_id=FASTAPI_EVENTS_MIDDLEWARE_ID,
    )

    logger.debug("Frostbite adding Starlette Context Middleware")
    application.add_middleware(RawContextMiddleware)

    logger.info("Frostbite adding startup and shutdown events")

    logger.debug(f"Frostbite adding Packet Handler ASGI Middleware for {WORLD_PACKETS_MIDDLEWARE_ID}")
    application.add_middleware(
        EventHandlerASGIMiddleware,
        handlers=[handlers.packet_handlers],
        middleware_id=WORLD_PACKETS_MIDDLEWARE_ID,
    )

    logger.info("Frostbite adding packet handlers")
    get_modules(handlers, global_namespace="FROSTBITE_HANDLERS_LIST")

    logger.info("Frostbite adding events")
    get_modules(events, global_namespace="FROSTBITE_EVENTS_LIST")

    sio_application = socketio.ASGIApp(sio, other_asgi_app=application)

    logger.info("Frostbite setup complete")
    logger.info("Frostbite is ready to be started in a ASGI service")

    return sio_application


app = get_application()


@app.get("/sentry-test")
async def trigger_error_error():
    division_by_zero = 1 / 0


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", log_level="debug", reload=True)
