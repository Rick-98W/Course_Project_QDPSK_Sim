"""Load the transmitter reference PNG as raw RGB bytes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class ReferenceImage:
    path: Path
    width: int
    height: int
    channels: int
    rgb_bytes: bytes


def load_reference_image(path: str | Path) -> ReferenceImage:
    source = Path(path)
    data = source.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("%s is not a PNG file" % source)

    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    idat_parts = []

    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("truncated PNG chunk header")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if crc_end > len(data):
            raise ValueError("truncated PNG chunk payload")

        chunk_data = data[chunk_start:chunk_end]
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break
        offset = crc_end

    if width is None:
        raise ValueError("PNG is missing IHDR")
    if bit_depth != 8:
        raise ValueError("only 8-bit PNG images are supported")
    if color_type not in (2, 6):
        raise ValueError("only RGB and RGBA PNG images are supported")
    if interlace != 0:
        raise ValueError("interlaced PNG images are not supported")

    bytes_per_pixel = 3 if color_type == 2 else 4
    inflated = zlib.decompress(b"".join(idat_parts))
    rgb_bytes = _unfilter_png_scanlines(inflated, width, height, bytes_per_pixel)
    if color_type == 6:
        rgb_bytes = _strip_alpha(rgb_bytes)

    return ReferenceImage(
        path=source,
        width=int(width),
        height=int(height),
        channels=3,
        rgb_bytes=rgb_bytes,
    )


def _unfilter_png_scanlines(data, width, height, bytes_per_pixel):
    stride = width * bytes_per_pixel
    expected = height * (1 + stride)
    if len(data) != expected:
        raise ValueError("unexpected decompressed PNG size")

    rows = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = data[offset]
        offset += 1
        raw = bytearray(data[offset : offset + stride])
        offset += stride
        row = _unfilter_row(raw, previous, bytes_per_pixel, filter_type)
        rows.append(bytes(row))
        previous = row
    return b"".join(rows)


def _unfilter_row(raw, previous, bytes_per_pixel, filter_type):
    row = bytearray(len(raw))
    for index, value in enumerate(raw):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index]
        up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = _paeth(left, up, up_left)
        else:
            raise ValueError("unsupported PNG filter type %d" % filter_type)

        row[index] = (value + predictor) & 0xFF
    return bytes(row)


def _paeth(left, up, up_left):
    prediction = left + up - up_left
    pa = abs(prediction - left)
    pb = abs(prediction - up)
    pc = abs(prediction - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def _strip_alpha(rgba_bytes):
    rgb = bytearray()
    for index in range(0, len(rgba_bytes), 4):
        rgb.extend(rgba_bytes[index : index + 3])
    return bytes(rgb)
