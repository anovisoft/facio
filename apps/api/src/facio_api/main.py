from fastapi import FastAPI

from facio_api.desk import routers as desk
from facio_api.routers import health, talk


def create_app() -> FastAPI:
    application = FastAPI(title="Facio talk")
    application.include_router(health.router)
    application.include_router(talk.router)
    application.include_router(desk.router)
    return application


app = create_app()
