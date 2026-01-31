# ABOUTME: Database connection pool dependency injection.
# ABOUTME: Provides a FastAPI dependency that yields the psycopg AsyncConnectionPool.
"""Database connection pool management."""

from typing import Annotated, Any

from fastapi import Depends, Request
from psycopg_pool import AsyncConnectionPool


def get_pool(request: Request) -> AsyncConnectionPool[Any]:
    """Get the connection pool from app state."""
    return request.app.state.pool


Pool = Annotated[AsyncConnectionPool[Any], Depends(get_pool)]
