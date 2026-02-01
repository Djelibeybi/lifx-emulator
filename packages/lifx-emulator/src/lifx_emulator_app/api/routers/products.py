"""Product registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from lifx_emulator.products.registry import PRODUCTS


def create_products_router() -> APIRouter:
    """Create products router.

    Returns:
        Configured APIRouter for product endpoints
    """
    router = APIRouter(prefix="/api/products", tags=["products"])

    @router.get(
        "",
        status_code=200,
        summary="List all known products",
        description="Returns a list of all LIFX products from the product registry.",
    )
    async def list_products():
        """List all products from the registry."""
        return [
            {
                "pid": info.pid,
                "name": info.name,
                "vendor": info.vendor,
                "has_color": info.has_color,
                "has_infrared": info.has_infrared,
                "has_multizone": info.has_multizone,
                "has_chain": info.has_chain,
                "has_matrix": info.has_matrix,
                "has_relays": info.has_relays,
                "has_buttons": info.has_buttons,
                "has_hev": info.has_hev,
            }
            for info in sorted(PRODUCTS.values(), key=lambda p: p.pid)
        ]

    return router
