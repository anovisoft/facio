from fastapi import APIRouter, FastAPI

from facio_api.main import create_app
from facio_api.routers import health, talk


def test_create_app_is_callable() -> None:
    application = create_app()
    assert isinstance(application, FastAPI)
    assert application is not create_app()


def test_health_and_talk_are_different_routers() -> None:
    assert isinstance(health.router, APIRouter)
    assert isinstance(talk.router, APIRouter)
    assert health.router is not talk.router
    assert health.router.tags == ["health"]
    assert talk.router.tags == ["talk"]


def test_phone_paths_unchanged() -> None:
    application = create_app()
    paths = application.openapi()["paths"]
    assert "get" in paths["/v1/health"]
    assert "post" in paths["/v1/talk/turn"]
