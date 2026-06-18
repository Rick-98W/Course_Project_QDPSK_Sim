"""Application-layer packetization for IQ streaming."""

from __future__ import annotations

import struct
from typing import List

import numpy as np


MAGIC = b"\xAA\xBB"
MODE_DUAL_CHANNEL = 0x03
VERSION = 0x01

CHANNEL_QPSK = 0
CHANNEL_QDPSK = 1

SAMPLE_FORMAT_COMPLEX64 = 1

COMPLEX64_BYTES_PER_SAMPLE = 8
HEADER_STRUCT = struct.Struct(">2sBBIBBHHIII")


def complex_iq_to_bytes(iq):
    """Serialize complex IQ samples as native complex64 bytes."""
    return np.asarray(iq, dtype=np.complex64).tobytes()


def fragment_iq_stream(
    iq,
    frame_id,
    channel_id,
    max_payload_bytes=1400,
    sample_format=SAMPLE_FORMAT_COMPLEX64,
):
    """Split a complex IQ stream into UDP-sized fragments.

    The default payload cap is chosen to stay below common Ethernet MTU
    boundaries once the application header is included.
    """
    if sample_format != SAMPLE_FORMAT_COMPLEX64:
        raise ValueError("only complex64 is supported in round 6")

    payload_limit = int(max_payload_bytes)
    payload_limit -= payload_limit % COMPLEX64_BYTES_PER_SAMPLE
    if payload_limit < COMPLEX64_BYTES_PER_SAMPLE:
        raise ValueError("max_payload_bytes is too small for complex64 payloads")

    iq_bytes = complex_iq_to_bytes(iq)
    total_samples = len(iq_bytes) // COMPLEX64_BYTES_PER_SAMPLE
    total_chunks = (len(iq_bytes) + payload_limit - 1) // payload_limit
    packets = []

    for chunk_index in range(total_chunks):
        start = chunk_index * payload_limit
        end = min(start + payload_limit, len(iq_bytes))
        chunk = iq_bytes[start:end]
        chunk_samples = len(chunk) // COMPLEX64_BYTES_PER_SAMPLE
        header = HEADER_STRUCT.pack(
            MAGIC,
            MODE_DUAL_CHANNEL,
            VERSION,
            int(frame_id) & 0xFFFFFFFF,
            int(channel_id) & 0xFF,
            int(sample_format) & 0xFF,
            int(chunk_index) & 0xFFFF,
            int(total_chunks) & 0xFFFF,
            int(start // COMPLEX64_BYTES_PER_SAMPLE) & 0xFFFFFFFF,
            int(total_samples) & 0xFFFFFFFF,
            int(chunk_samples) & 0xFFFFFFFF,
        )
        packets.append(header + chunk)

    return packets


def describe_fragment(packet_bytes):
    """Decode the packet header for diagnostics."""
    header = HEADER_STRUCT.unpack(packet_bytes[: HEADER_STRUCT.size])
    return {
        "magic": header[0],
        "mode": header[1],
        "version": header[2],
        "frame_id": header[3],
        "channel_id": header[4],
        "sample_format": header[5],
        "chunk_index": header[6],
        "chunk_count": header[7],
        "start_sample": header[8],
        "total_samples": header[9],
        "chunk_samples": header[10],
        "payload_bytes": len(packet_bytes) - HEADER_STRUCT.size,
    }


def fragment_iq_to_complex64(packet_bytes):
    """Decode a fragment payload back to complex64 samples."""
    payload = packet_bytes[HEADER_STRUCT.size :]
    if len(payload) % COMPLEX64_BYTES_PER_SAMPLE:
        raise ValueError("payload length is not aligned to complex64 samples")
    real_imag = np.frombuffer(payload, dtype=np.float32)
    if real_imag.size % 2:
        raise ValueError("payload float count is not even")
    complex_view = real_imag.view(np.complex64)
    return complex_view.copy()


def format_fragment_preview(packet_bytes, sample_limit=8, hex_limit=64):
    """Return a compact human-readable preview of a fragment."""
    header = describe_fragment(packet_bytes)
    samples = fragment_iq_to_complex64(packet_bytes)
    preview_samples = samples[: int(sample_limit)]
    payload = packet_bytes[HEADER_STRUCT.size : HEADER_STRUCT.size + int(hex_limit)]

    lines = [
        "magic=%r" % header["magic"],
        "mode=%d" % header["mode"],
        "version=%d" % header["version"],
        "frame_id=%d" % header["frame_id"],
        "channel_id=%d" % header["channel_id"],
        "sample_format=%d" % header["sample_format"],
        "chunk_index=%d/%d" % (header["chunk_index"], header["chunk_count"]),
        "start_sample=%d" % header["start_sample"],
        "chunk_samples=%d" % header["chunk_samples"],
        "total_samples=%d" % header["total_samples"],
        "payload_bytes=%d" % header["payload_bytes"],
        "first_samples=%s" % np.array2string(preview_samples, precision=6, separator=", "),
        "payload_hex=%s" % payload.hex(),
    ]
    return "\n".join(lines)
