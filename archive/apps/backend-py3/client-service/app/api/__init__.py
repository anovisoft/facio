from fastapi import APIRouter

from app.api.actions import router as actions_router
from app.api.events import router as events_router
from app.api.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(projects_router)
api_router.include_router(actions_router)
api_router.include_router(events_router)
