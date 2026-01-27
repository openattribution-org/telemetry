"""Database connection pool management."""

from typing import Annotated, Any

from fastapi import Depends, Request
from psycopg_pool import AsyncConnectionPool


def get_pool(request: Request) -> AsyncConnectionPool[Any]:
    """Get the connection pool from app state."""
    return request.app.state.pool


Pool = Annotated[AsyncConnectionPool[Any], Depends(get_pool)]
