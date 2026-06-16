"""Dependency-light PNG rendering for transmitter-side plots.

This module intentionally avoids matplotlib. The current Windows conda
environment can crash inside matplotlib/numpy linalg while laying out figures,
so the transmitter uses a small raster renderer based on NumPy and the PNG
format implemented with the standard library.
"""

from pathlib import Path
import struct
import zlib

import numpy as np


WHITE = np.array([255, 255, 255], dtype=np.uint8)
GRID = np.array([226, 232, 240], dtype=np.uint8)
AXIS = np.array([71, 85, 105], dtype=np.uint8)
TEXT = np.array([15, 23, 42], dtype=np.uint8)
GREEN = np.array([11, 110, 79], dtype=np.uint8)
BLUE = np.array([29, 78, 216], dtype=np.uint8)
ORANGE = np.array([180, 83, 9], dtype=np.uint8)


class Canvas:
    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)
        self.image = np.full((self.height, self.width, 3), WHITE, dtype=np.uint8)

    def line(self, x0, y0, x1, y1, color, alpha=1.0):
        x0 = int(round(x0))
        y0 = int(round(y0))
        x1 = int(round(x1))
        y1 = int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            self.point(x0, y0, color, alpha=alpha)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * error
            if e2 >= dy:
                error += dy
                x0 += sx
            if e2 <= dx:
                error += dx
                y0 += sy

    def rect_outline(self, left, top, right, bottom, color):
        self.line(left, top, right, top, color)
        self.line(right, top, right, bottom, color)
        self.line(right, bottom, left, bottom, color)
        self.line(left, bottom, left, top, color)

    def point(self, x, y, color, radius=0, alpha=1.0):
        x = int(x)
        y = int(y)
        radius = int(radius)
        for yy in range(y - radius, y + radius + 1):
            if yy < 0 or yy >= self.height:
                continue
            for xx in range(x - radius, x + radius + 1):
                if xx < 0 or xx >= self.width:
                    continue
                if radius and (xx - x) ** 2 + (yy - y) ** 2 > radius**2:
                    continue
                old = self.image[yy, xx].astype(np.float64)
                new = np.asarray(color, dtype=np.float64)
                self.image[yy, xx] = np.clip(old * (1.0 - alpha) + new * alpha, 0, 255)

    def text_label(self, x, y, text, color=TEXT):
        # Minimal label marks: keep title text out of the raster renderer for now.
        # The HTML UI can show titles above images; axes/grid are drawn here.
        del x, y, text, color


def render_eye_png(eye_traces, output_path, sps, title):
    del title
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(960, 480)
    left, top, right, bottom = 70, 45, 930, 420
    _draw_grid(canvas, left, top, right, bottom, x_lines=8, y_lines=6)

    traces = np.asarray(eye_traces, dtype=np.float64)
    if traces.size:
        max_abs = max(float(np.max(np.abs(traces))), 1e-6)
        x_values = np.arange(traces.shape[1], dtype=np.float64) / float(sps)
        x_min = 0.0
        x_max = max(float(np.max(x_values)), 1e-6)
        for trace in traces:
            points = [
                (
                    _map_value(x, x_min, x_max, left, right),
                    _map_value(y, -max_abs, max_abs, bottom, top),
                )
                for x, y in zip(x_values, trace)
            ]
            _draw_polyline(canvas, points, GREEN, alpha=0.22)

    canvas.rect_outline(left, top, right, bottom, AXIS)
    _write_png(output, canvas.image)


def render_constellation_png(symbols, output_path, title):
    del title
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(620, 620)
    left, top, right, bottom = 70, 45, 580, 555
    _draw_grid(canvas, left, top, right, bottom, x_lines=8, y_lines=8)

    x_zero = _map_value(0.0, -1.25, 1.25, left, right)
    y_zero = _map_value(0.0, -1.25, 1.25, bottom, top)
    canvas.line(left, y_zero, right, y_zero, AXIS, alpha=0.8)
    canvas.line(x_zero, top, x_zero, bottom, AXIS, alpha=0.8)

    points = np.asarray(symbols, dtype=np.complex64)
    for point in points:
        x = _map_value(float(point.real), -1.25, 1.25, left, right)
        y = _map_value(float(point.imag), -1.25, 1.25, bottom, top)
        canvas.point(x, y, BLUE, radius=2, alpha=0.18)

    canvas.rect_outline(left, top, right, bottom, AXIS)
    _write_png(output, canvas.image)


def render_psd_png(freqs, psd_db, output_path, title):
    del title
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(960, 480)
    left, top, right, bottom = 70, 45, 930, 420
    _draw_grid(canvas, left, top, right, bottom, x_lines=10, y_lines=6)

    freq_array = np.asarray(freqs, dtype=np.float64)
    psd_array = np.asarray(psd_db, dtype=np.float64)
    if freq_array.size and psd_array.size:
        x_min = float(np.min(freq_array))
        x_max = float(np.max(freq_array))
        y_min = -90.0
        y_max = 5.0
        points = [
            (
                _map_value(x, x_min, x_max, left, right),
                _map_value(np.clip(y, y_min, y_max), y_min, y_max, bottom, top),
            )
            for x, y in zip(freq_array, psd_array)
        ]
        _draw_polyline(canvas, points, ORANGE, alpha=1.0)

    canvas.rect_outline(left, top, right, bottom, AXIS)
    _write_png(output, canvas.image)


def render_all_tx_plots(
    symbols,
    waveform,
    output_dir,
    sps,
    eye_traces,
    eye_span_symbols,
    constellation_points,
    freqs,
    psd_db,
    channel_name,
):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    eye_path = output / "eye.png"
    constellation_path = output / "constellation.png"
    psd_path = output / "psd.png"

    render_eye_png(
        eye_traces,
        eye_path,
        sps=sps,
        title="%s Transmit Baseband Eye Diagram" % channel_name,
    )
    render_constellation_png(
        constellation_points,
        constellation_path,
        title="%s Clean Transmit Constellation" % channel_name,
    )
    render_psd_png(
        freqs,
        psd_db,
        psd_path,
        title="%s Transmit Baseband PSD" % channel_name,
    )

    return {
        "eye": str(eye_path),
        "constellation": str(constellation_path),
        "psd": str(psd_path),
        "symbol_count": int(np.asarray(symbols).size),
        "waveform_sample_count": int(np.asarray(waveform).size),
        "eye_trace_count": int(eye_traces.shape[0]),
        "eye_span_symbols": int(eye_span_symbols),
    }


def _draw_grid(canvas, left, top, right, bottom, x_lines, y_lines):
    for index in range(x_lines + 1):
        x = left + (right - left) * index / float(x_lines)
        canvas.line(x, top, x, bottom, GRID, alpha=1.0)
    for index in range(y_lines + 1):
        y = top + (bottom - top) * index / float(y_lines)
        canvas.line(left, y, right, y, GRID, alpha=1.0)


def _draw_polyline(canvas, points, color, alpha=1.0):
    if len(points) < 2:
        return
    previous = points[0]
    for current in points[1:]:
        canvas.line(previous[0], previous[1], current[0], current[1], color, alpha=alpha)
        previous = current


def _map_value(value, src_min, src_max, dst_min, dst_max):
    if src_max == src_min:
        return float(dst_min)
    ratio = (float(value) - float(src_min)) / (float(src_max) - float(src_min))
    return float(dst_min) + ratio * (float(dst_max) - float(dst_min))


def _write_png(path, image):
    image = np.asarray(image, dtype=np.uint8)
    height, width, channels = image.shape
    if channels != 3:
        raise ValueError("PNG writer expects RGB image data")

    raw_rows = []
    for row in image:
        raw_rows.append(b"\x00" + row.tobytes())
    compressed = zlib.compress(b"".join(raw_rows), level=6)

    with open(path, "wb") as file:
        file.write(b"\x89PNG\r\n\x1a\n")
        file.write(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
        file.write(_png_chunk(b"IDAT", compressed))
        file.write(_png_chunk(b"IEND", b""))


def _png_chunk(chunk_type, data):
    payload = chunk_type + data
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", crc)
