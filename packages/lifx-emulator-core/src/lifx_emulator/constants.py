"""Protocol constants for LIFX LAN Protocol"""

from typing import Final

# ============================================================================
# Network Constants
# ============================================================================

# LIFX UDP port for device communication
LIFX_UDP_PORT: Final[int] = 56700

# LIFX Protocol version
LIFX_PROTOCOL_VERSION: Final[int] = 1024

# Header size in bytes
LIFX_HEADER_SIZE: Final[int] = 36

# Backward compatibility alias
HEADER_SIZE = LIFX_HEADER_SIZE

# ============================================================================
# Matrix Constants
# ============================================================================

# Longest tile chain a chain-capable matrix product (the original LIFX Tile)
# drives. Every matrix product without the chain capability is a single tile.
MAX_CHAIN_TILES: Final[int] = 5


def max_tile_count(has_chain: bool) -> int:
    """Return the most tiles a matrix product can have.

    Args:
        has_chain: Whether the product has the chain capability

    Returns:
        MAX_CHAIN_TILES for a chain-capable product, 1 otherwise
    """
    return MAX_CHAIN_TILES if has_chain else 1


def is_valid_tile_count(tile_count: object, has_chain: bool) -> bool:
    """Whether a value is a tile count a matrix product can have.

    Saved state and config come from files a person can edit, so the value
    is checked as an integer (not a bool, which Python counts as one) before
    its range.

    Args:
        tile_count: The value to check
        has_chain: Whether the product has the chain capability

    Returns:
        True if tile_count is an int from 1 to max_tile_count(has_chain)
    """
    if not isinstance(tile_count, int) or isinstance(tile_count, bool):
        return False
    return 1 <= tile_count <= max_tile_count(has_chain)


# ============================================================================
# Official LIFX Repository URLs
# ============================================================================

# Official LIFX protocol specification URL
PROTOCOL_URL: Final[str] = (
    "https://raw.githubusercontent.com/LIFX/public-protocol/refs/heads/main/protocol.yml"
)

# Official LIFX products specification URL
PRODUCTS_URL: Final[str] = (
    "https://raw.githubusercontent.com/LIFX/products/refs/heads/master/products.json"
)
