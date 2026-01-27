"""OpenAttribution Telemetry Server - FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from openattribution.telemetry_server.config import settings
from openattribution.telemetry_server.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage server lifecycle."""
    # Initialize database pool
    app.state.pool = AsyncConnectionPool(
        settings.database_url,
        open=False,
        min_size=1,
        max_size=10,
    )
    await app.state.pool.open(wait=True, timeout=10)
    logger.info("Database pool initialized")

    yield

    # Cleanup
    await app.state.pool.close()
    logger.info("Server shutdown complete")


app = FastAPI(
    title="OpenAttribution Telemetry Server",
    description="Reference server implementation for the OpenAttribution Telemetry standard",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
