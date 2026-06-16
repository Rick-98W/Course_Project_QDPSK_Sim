"""Write recovered RGB images and compute quality metrics."""

from __future__ import annotations

import binascii
from pathlib import Path
import struct
import zlib

import numpy as np


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def write_png_rgb(path: str | Path, width: int, height: int, rgb_bytes: bytes) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if len(rgb_bytes) != width * height * 3:
        raise ValueError("RGB payload length does not match image dimensions")

    raw = bytearray()
    row_stride = width * 3
    for row_index in range(height):
        raw.append(0)
        start = row_index * row_stride
        raw.extend(rgb_bytes[start : start + row_stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=9)

    with output.open("wb") as file:
        file.write(PNG_SIGNATURE)
        _write_chunk(file, b"IHDR", ihdr)
        _write_chunk(file, b"IDAT", idat)
        _write_chunk(file, b"IEND", b"")

    return output


def compute_mse_psnr(reference_rgb: bytes, recovered_rgb: bytes) -> tuple[float, float]:
    reference = np.frombuffer(reference_rgb, dtype=np.uint8)
    recovered = np.frombuffer(recovered_rgb, dtype=np.uint8)
    if reference.size != recovered.size:
        raise ValueError("reference and recovered payloads must have the same length")

    diff = reference.astype(np.float64) - recovered.astype(np.float64)
    mse = float(np.mean(diff * diff))
    if mse == 0.0:
        return 0.0, float("inf")
    psnr = float(10.0 * np.log10((255.0 * 255.0) / mse))
    return mse, psnr


def _write_chunk(file, chunk_type: bytes, chunk_data: bytes) -> None:
    file.write(struct.pack(">I", len(chunk_data)))
    file.write(chunk_type)
    file.write(chunk_data)
    crc = binascii.crc32(chunk_type)
    crc = binascii.crc32(chunk_data, crc) & 0xFFFFFFFF
    file.write(struct.pack(">I", crc))
