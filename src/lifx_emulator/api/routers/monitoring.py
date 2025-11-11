"""Monitoring endpoints for server statistics and activity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

if TYPE_CHECKING:
    from lifx_emulator.server import EmulatedLifxServer

from lifx_emulator.api.models import ActivityEvent, ServerStats


def create_monitoring_router(server: EmulatedLifxServer) -> APIRouter:
    """Create monitoring router with server dependency.

    Args:
        server: The LIFX emulator server instance

    Returns:
        Configured APIRouter for monitoring endpoints
    """
    # Create fresh router instance for this server
    router = APIRouter(prefix="/api", tags=["monitoring"])

    @router.get(
        "/stats",
        response_model=ServerStats,
        summary="Get server statistics",
        description=(
            "Returns server uptime, packet counts, error counts, and device count."
        ),
    )
    async def get_stats():
        """Get server statistics."""
        return server.get_stats()

    @router.get(
        "/activity",
        response_model=list[ActivityEvent],
        summary="Get recent activity",
        description=(
            "Returns the last 100 packet events (TX/RX) "
            "with timestamps and packet details."
        ),
    )
    async def get_activity():
        """Get recent activity events."""
        return [ActivityEvent(**event) for event in server.get_recent_activity()]

    return router
