"""Network helpers for Receiver LAN testing."""

from __future__ import annotations

import socket


def local_ipv4_addresses() -> list[str]:
    """Return non-loopback IPv4 addresses that TX can target on the LAN."""
    addresses: set[str] = set()
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_DGRAM):
            address = info[4][0]
            if _is_lan_ipv4(address):
                addresses.add(address)
    except OSError:
        pass

    probe_address = _probe_default_ipv4()
    if _is_lan_ipv4(probe_address):
        addresses.add(probe_address)

    return sorted(addresses)


def tx_target_hint(listen_port: int) -> str:
    addresses = local_ipv4_addresses()
    if addresses:
        return "%s:%d" % (addresses[0], int(listen_port))
    return "PC_LAN_IP:%d" % int(listen_port)


def _probe_default_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def _is_lan_ipv4(address: str | None) -> bool:
    if not address or address.startswith("127."):
        return False
    parts = address.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False
