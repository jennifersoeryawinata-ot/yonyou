from telemetry import setup_telemetry
from configs.config import EnvironmentMode
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.logger import logger as fastapi_logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi_async_sqlalchemy import SQLAlchemyMiddleware
from fastapi_pagination import add_pagination
from middleware.logging_middleware import LoggingMiddleware
from configs.config import settings
from api import api
from services.rabbitmq_service import RabbitMQService

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # FastAPI handles requests here

    await RabbitMQService.close()


def init_app():

    logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

    if settings.ENV_MODE == EnvironmentMode.PRODUCTION.value:
        setup_telemetry()

    description = """
        This is a Skeleton for backend with FastAPI.
    """

    app = FastAPI(
        title="Skeleton Fastapi",
        contact={
            "name": "developer",
            "email": "mai@ot.cid"
        },
        license_info={
            "name": "BSD License",
        },
        terms_of_service="https://www.google.com/policies/terms/",
        description=description,
        version="1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=True,
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        SQLAlchemyMiddleware,
        db_url=settings.DB_CONFIG,
        engine_args={
            "echo": False,
            "pool_pre_ping": True,
            "pool_recycle": 1800,
            "connect_args": {"server_settings": { "search_path": settings.POSTGRES_SCHEMA}}
        }
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)

    app.include_router(api.api_router, prefix="/skeleton",)
    app.include_router(api.oidc_router)

    add_pagination(app)

    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    gunicorn_logger = logging.getLogger("gunicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = gunicorn_error_logger.handlers

    fastapi_logger.handlers = gunicorn_error_logger.handlers

    if __name__ != "__main__":
        fastapi_logger.setLevel(gunicorn_logger.level)
    else:
        fastapi_logger.setLevel(logging.DEBUG)

    return app


app = init_app()
