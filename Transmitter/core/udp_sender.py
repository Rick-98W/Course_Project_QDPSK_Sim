"""UDP transmission helpers."""

from __future__ import annotations

import socket
import time


def send_packets(datagrams, host, port, delay_sec=0.0):
    """Send a sequence of datagrams to a UDP endpoint."""
    endpoint = (host, int(port))
    count = 0
    total_bytes = 0
    started = time.perf_counter()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for packet in datagrams:
            sent = sock.sendto(packet, endpoint)
            total_bytes += sent
            count += 1
            if delay_sec > 0.0:
                time.sleep(delay_sec)

    elapsed = time.perf_counter() - started
    return {
        "packet_count": count,
        "total_bytes": total_bytes,
        "elapsed_sec": elapsed,
        "bytes_per_sec": (total_bytes / elapsed) if elapsed > 0 else 0.0,
    }
