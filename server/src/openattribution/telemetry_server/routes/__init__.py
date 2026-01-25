"""API routes for OpenAttribution Telemetry Server."""

from fastapi import APIRouter

from openattribution.telemetry_server.routes.events import router as events_router
from openattribution.telemetry_server.routes.internal import router as internal_router
from openattribution.telemetry_server.routes.sessions import router as sessions_router

router = APIRouter()
router.include_router(sessions_router)
router.include_router(events_router)
router.include_router(internal_router, prefix="/internal")
