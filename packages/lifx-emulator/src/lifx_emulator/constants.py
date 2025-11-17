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
