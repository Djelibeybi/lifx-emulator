"""Frozen direct lifx-async responder extension used only by the MDNS-10 spike."""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass

SERVICE_TYPE = "_lifx._udp.local"
DNS_CLASS_IN = 1
DNS_TYPE_A = 1
DNS_TYPE_PTR = 12
DNS_TYPE_TXT = 16
DNS_TYPE_AAAA = 28
DNS_TYPE_SRV = 33


@dataclass(frozen=True)
class Advertisement:
    """One synthetic LIFX DNS-SD advertisement."""

    serial: str
    port: int
    address: str
    product: str = "27"
    firmware: str = "4.200"
    transport: str = "1"


def _name(value: str) -> bytes:
    return (
        b"".join(
            bytes((len(label.encode()),)) + label.encode()
            for label in value.rstrip(".").split(".")
        )
        + b"\x00"
    )


def _question_end(query: bytes) -> int:
    offset = 12
    while offset < len(query) and query[offset]:
        offset += query[offset] + 1
    end = offset + 5
    if end > len(query):
        raise ValueError("truncated DNS question")
    return end


def _question_name(query: bytes) -> str:
    offset = 12
    labels: list[str] = []
    while offset < len(query) and query[offset]:
        length = query[offset]
        offset += 1
        labels.append(query[offset : offset + length].decode())
        offset += length
    return ".".join(labels)


def _record(name: str, record_type: int, ttl: int, data: bytes) -> bytes:
    return (
        _name(name)
        + struct.pack("!HHIH", record_type, DNS_CLASS_IN, ttl, len(data))
        + data
    )


def build_legacy_unicast_responses(
    query: bytes, advertisements: list[Advertisement], ttl: int = 10
) -> list[bytes]:
    """Return exactly one complete legacy-unicast reply for each device."""
    question_end = _question_end(query)
    query_id = struct.unpack("!H", query[:2])[0]
    question = query[12:question_end]
    question_name = _question_name(query).lower()
    question_type = struct.unpack("!H", query[question_end - 4 : question_end - 2])[0]
    responses: list[bytes] = []
    for advertisement in advertisements:
        instance = f"{advertisement.serial}.{SERVICE_TYPE}"
        hostname = f"{advertisement.serial}.local"
        ptr = _record(SERVICE_TYPE, DNS_TYPE_PTR, ttl, _name(instance))
        srv_data = struct.pack("!HHH", 0, 0, advertisement.port) + _name(hostname)
        srv = _record(instance, DNS_TYPE_SRV, ttl, srv_data)
        values = (
            f"id={advertisement.serial}",
            f"p={advertisement.product}",
            f"fw={advertisement.firmware}",
            f"tm={advertisement.transport}",
        )
        txt_data = b"".join(
            bytes((len(value.encode()),)) + value.encode() for value in values
        )
        txt = _record(instance, DNS_TYPE_TXT, ttl, txt_data)
        parsed = socket.inet_pton(
            socket.AF_INET6 if ":" in advertisement.address else socket.AF_INET,
            advertisement.address,
        )
        address_type = DNS_TYPE_AAAA if ":" in advertisement.address else DNS_TYPE_A
        address = _record(hostname, address_type, ttl, parsed)
        if question_type in (DNS_TYPE_A, DNS_TYPE_AAAA):
            if question_name != hostname.lower() or question_type != address_type:
                continue
            header = struct.pack("!HHHHHH", query_id, 0x8400, 1, 1, 0, 0)
            responses.append(header + question + address)
            continue
        header = struct.pack("!HHHHHH", query_id, 0x8400, 1, 1, 0, 3)
        responses.append(header + question + ptr + srv + txt + address)
    return responses
