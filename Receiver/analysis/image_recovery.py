"""Recover transmitter image frames from demodulated bitstreams."""

from __future__ import annotations

import struct
from dataclasses import dataclass


IMAGE_MAGIC = b"IMG0"
EXPECTED_WIDTH = 64
EXPECTED_HEIGHT = 64
EXPECTED_CHANNELS = 3


@dataclass(frozen=True)
class ImageFrame:
    width: int
    height: int
    channels: int
    rgb_bytes: bytes
    header_valid: bool = True

    @property
    def payload_bytes(self) -> int:
        return len(self.rgb_bytes)


def parse_image_frame(data: bytes) -> ImageFrame:
    """Parse the fixed transmitter image frame format."""
    if len(data) < 9:
        raise ValueError("image frame too short")
    if not data.startswith(IMAGE_MAGIC):
        raise ValueError("bad image magic")
    width, height, channels = struct.unpack(">HHB", data[4:9])
    rgb_bytes = data[9:]
    if channels != 3:
        raise ValueError("unsupported channel count %d" % channels)
    expected_payload = width * height * channels
    if len(rgb_bytes) < expected_payload:
        raise ValueError("RGB payload length does not match image dimensions")
    return ImageFrame(
        width=width,
        height=height,
        channels=channels,
        rgb_bytes=rgb_bytes[:expected_payload],
        header_valid=True,
    )


def recover_image_lenient(data: bytes) -> ImageFrame:
    """Recover an image frame, falling back to fixed 64x64 RGB when header bits fail."""
    try:
        return parse_image_frame(data)
    except Exception:
        payload_bytes = EXPECTED_WIDTH * EXPECTED_HEIGHT * EXPECTED_CHANNELS
        start = 9 if len(data) >= 9 else 0
        payload = data[start : start + payload_bytes]
        if len(payload) < payload_bytes:
            payload = payload + bytes(payload_bytes - len(payload))
        return ImageFrame(
            width=EXPECTED_WIDTH,
            height=EXPECTED_HEIGHT,
            channels=EXPECTED_CHANNELS,
            rgb_bytes=payload,
            header_valid=False,
        )
