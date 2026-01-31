# ABOUTME: Package entry point for the OpenAttribution Telemetry reference server.
# ABOUTME: Exports the FastAPI app instance for uvicorn and test clients.
"""OpenAttribution Telemetry Server - Reference implementation."""

from openattribution.telemetry_server.main import app

__all__ = ["app"]
