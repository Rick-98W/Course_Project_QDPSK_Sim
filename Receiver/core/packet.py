"""Application-layer UDP fragment parsing for Receiver."""

from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np


MAGIC = b"\xAA\xBB"
MODE_DUAL_CHANNEL = 0x03
VERSION = 0x01

CHANNEL_QPSK = 0
CHANNEL_QDPSK = 1
CHANNEL_NAMES = {
    CHANNEL_QPSK: "QPSK",
    CHANNEL_QDPSK: "QDPSK",
}

SAMPLE_FORMAT_COMPLEX64 = 1
COMPLEX64_BYTES_PER_SAMPLE = 8

HEADER_STRUCT = struct.Struct(">2sBBIBBHHIII")
HEADER_SIZE = HEADER_STRUCT.size


class PacketError(ValueError):
    """Raised when a UDP datagram does not match the Receiver protocol."""


@dataclass(frozen=True)
class FragmentHeader:
    magic: bytes
    mode: int
    version: int
    frame_id: int
    channel_id: int
    sample_format: int
    chunk_index: int
    chunk_count: int
    start_sample: int
    total_samples: int
    chunk_samples: int
    payload_bytes: int

    @property
    def channel_name(self) -> str:
        return CHANNEL_NAMES.get(self.channel_id, "UNKNOWN")

    @property
    def key(self) -> tuple[int, int]:
        return (self.frame_id, self.channel_id)


def parse_header(packet: bytes) -> FragmentHeader:
    """Parse and validate the 26-byte application header."""
    if len(packet) < HEADER_SIZE:
        raise PacketError(
            "packet too short: %d bytes, need at least %d" % (len(packet), HEADER_SIZE)
        )

    values = HEADER_STRUCT.unpack(packet[:HEADER_SIZE])
    payload_bytes = len(packet) - HEADER_SIZE
    header = FragmentHeader(
        magic=values[0],
        mode=values[1],
        version=values[2],
        frame_id=values[3],
        channel_id=values[4],
        sample_format=values[5],
        chunk_index=values[6],
        chunk_count=values[7],
        start_sample=values[8],
        total_samples=values[9],
        chunk_samples=values[10],
        payload_bytes=payload_bytes,
    )
    validate_header(header)
    return header


def validate_header(header: FragmentHeader) -> None:
    """Validate protocol constants and payload alignment."""
    if header.magic != MAGIC:
        raise PacketError("bad magic: %r" % (header.magic,))
    if header.mode != MODE_DUAL_CHANNEL:
        raise PacketError("bad mode: %d" % header.mode)
    if header.version != VERSION:
        raise PacketError("bad version: %d" % header.version)
    if header.channel_id not in CHANNEL_NAMES:
        raise PacketError("bad channel_id: %d" % header.channel_id)
    if header.sample_format != SAMPLE_FORMAT_COMPLEX64:
        raise PacketError("bad sample_format: %d" % header.sample_format)
    if header.chunk_count <= 0:
        raise PacketError("chunk_count must be positive")
    if header.chunk_index >= header.chunk_count:
        raise PacketError(
            "chunk_index %d outside chunk_count %d"
            % (header.chunk_index, header.chunk_count)
        )
    if header.payload_bytes % COMPLEX64_BYTES_PER_SAMPLE:
        raise PacketError("payload length is not complex64-aligned")

    actual_chunk_samples = header.payload_bytes // COMPLEX64_BYTES_PER_SAMPLE
    if header.chunk_samples != actual_chunk_samples:
        raise PacketError(
            "chunk_samples mismatch: header=%d actual=%d"
            % (header.chunk_samples, actual_chunk_samples)
        )

    expected_start = header.chunk_index * 175
    if header.chunk_samples == 175 and header.start_sample != expected_start:
        raise PacketError(
            "unexpected start_sample for full chunk: header=%d expected=%d"
            % (header.start_sample, expected_start)
        )


def parse_fragment(packet: bytes) -> tuple[FragmentHeader, bytes]:
    """Return a validated header and the raw complex64 payload bytes."""
    header = parse_header(packet)
    payload = packet[HEADER_SIZE:]
    return header, payload


def payload_to_complex64(payload: bytes) -> np.ndarray:
    """Decode a fragment or full-frame payload as complex64 samples."""
    if len(payload) % COMPLEX64_BYTES_PER_SAMPLE:
        raise PacketError("payload length is not complex64-aligned")
    return np.frombuffer(payload, dtype=np.complex64).copy()


def format_header(header: FragmentHeader) -> str:
    """Format a compact single-line header summary."""
    return (
        "magic=%r mode=%d version=%d frame_id=%d channel=%s(%d) "
        "sample_format=%d chunk_index=%d/%d start_sample=%d "
        "chunk_samples=%d total_samples=%d payload_bytes=%d"
        % (
            header.magic,
            header.mode,
            header.version,
            header.frame_id,
            header.channel_name,
            header.channel_id,
            header.sample_format,
            header.chunk_index,
            header.chunk_count,
            header.start_sample,
            header.chunk_samples,
            header.total_samples,
            header.payload_bytes,
        )
    )
