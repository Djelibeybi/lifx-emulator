"""Local interface selection for IPv4 peer filtering.

A UDP socket bound to a specific LAN address does not receive datagrams sent
to the limited broadcast address on Linux and macOS, so LIFX discovery fails
silently. The server therefore binds the wildcard address for any specific,
non-loopback IPv4 bind address and accepts only peers on the subnets of the
interface that owns that address. The decision is a pure function of the peer
address and the interface prefixes so it can be tested without sockets.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import AddressValueError, IPv4Address, IPv4Network

import ifaddr

__all__ = ["InterfaceSelection", "is_direct_bind_address", "select_interface"]


@dataclass(frozen=True)
class InterfaceSelection:
    """The interface owning a bind address and the IPv4 prefixes it serves.

    Attributes:
        address: The configured bind address that selected the interface.
        name: Human-readable interface name for logs and errors.
        prefixes: IPv4 networks assigned to the interface.
    """

    address: str
    name: str
    prefixes: tuple[IPv4Network, ...]

    def accepts(self, peer: str) -> bool:
        """Return True when the peer lies within any prefix of the interface.

        Args:
            peer: Peer IPv4 address as text.

        Returns:
            True when the peer is on one of the interface's subnets. An
            address that cannot be parsed is never accepted.
        """
        try:
            peer_address = IPv4Address(peer)
        except AddressValueError:
            return False
        return any(peer_address in prefix for prefix in self.prefixes)


def is_direct_bind_address(address: str) -> bool:
    """Return True when an IPv4 bind address should be bound as given.

    Loopback and the wildcard address bind directly; both already behave as
    operators expect for broadcast discovery.

    Args:
        address: IPv4 bind address as text.

    Returns:
        True for loopback and unspecified addresses, False otherwise.

    Raises:
        ValueError: If the address is not a valid IPv4 address.
    """
    try:
        parsed = IPv4Address(address)
    except AddressValueError as error:
        raise ValueError(f"Invalid IPv4 bind address {address!r}: {error}") from error
    return parsed.is_loopback or parsed.is_unspecified


def _ipv4_prefixes(adapter: ifaddr.Adapter) -> tuple[IPv4Network, ...]:
    """Collect the IPv4 networks assigned to one adapter."""
    prefixes: list[IPv4Network] = []
    for ip in adapter.ips:
        # ifaddr reports IPv6 addresses as tuples; only IPv4 strings apply here.
        if isinstance(ip.ip, str):
            prefixes.append(IPv4Network(f"{ip.ip}/{ip.network_prefix}", strict=False))
    return tuple(prefixes)


def select_interface(address: str) -> InterfaceSelection:
    """Find the local interface that owns an IPv4 address.

    Args:
        address: IPv4 address assigned to one of the host's interfaces.

    Returns:
        The owning interface and all of its IPv4 prefixes.

    Raises:
        ValueError: If the address is invalid or no local interface owns it.
    """
    try:
        wanted = IPv4Address(address)
    except AddressValueError as error:
        raise ValueError(f"Invalid IPv4 bind address {address!r}: {error}") from error

    for adapter in ifaddr.get_adapters():
        owned = any(
            isinstance(ip.ip, str) and IPv4Address(ip.ip) == wanted
            for ip in adapter.ips
        )
        if owned:
            return InterfaceSelection(
                address=address,
                name=adapter.nice_name,
                prefixes=_ipv4_prefixes(adapter),
            )

    raise ValueError(
        f"Bind address {address} is not assigned to any local network interface; "
        "use the address of a local interface, 127.0.0.1 or 0.0.0.0"
    )
