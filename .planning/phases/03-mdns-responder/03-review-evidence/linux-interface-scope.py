import asyncio
import socket
import struct

from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf


async def main():
    route = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    route.connect(("224.0.0.251", 5353))
    external = route.getsockname()[0]
    route.close()
    owner = AsyncZeroconf(interfaces=["127.0.0.1"], ip_version=IPVersion.V4Only)
    info = ServiceInfo(
        "_lifx._udp.local.",
        "d073d599ffff._lifx._udp.local.",
        addresses=[socket.inet_aton("127.0.0.1")],
        port=56700,
        properties={"id": "d073d599ffff"},
        server="d073d599ffff.local.",
        host_ttl=10,
        other_ttl=10,
    )
    daemon = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    daemon.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    daemon.bind(("", 5353))
    daemon.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        socket.inet_aton("224.0.0.251") + socket.inet_aton(external),
    )
    try:
        await (await owner.async_register_service(info, ttl=10))
        query = (
            struct.pack("!6H", 54321, 0, 1, 0, 0, 0)
            + b"\x05_lifx\x04_udp\x05local\x00"
            + struct.pack("!2H", 12, 1)
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.bind((external, 0))
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(external)
        )
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(sock, query, ("224.0.0.251", 5353))
        try:
            packet, peer = await asyncio.wait_for(loop.sock_recvfrom(sock, 65535), 2)
            print(
                {
                    "unexpected_reply": True,
                    "query_id_matches": struct.unpack_from("!H", packet)[0] == 54321,
                    "contains_loopback_identity": b"d073d599ffff" in packet,
                }
            )
        except asyncio.TimeoutError:
            print({"unexpected_reply": False})
        finally:
            sock.close()
    finally:
        await (await owner.async_unregister_service(info))
        await owner.async_close()
        daemon.close()


asyncio.run(main())
