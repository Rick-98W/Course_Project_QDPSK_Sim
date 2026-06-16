"""Matplotlib plot generation for receiver capture reports.

The Receiver environment currently crashes inside Matplotlib's Axes/tick
transform path, so these plots use Matplotlib's low-level artists on a
manual pixel coordinate system. This still uses Matplotlib for rendering,
fonts, and PNG output while avoiding the failing numpy.linalg transform path.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
import numpy as np

import config

CHINESE_FONT = config.CHINESE_FONT_FAMILY
LATIN_FONT = config.LATIN_FONT_FAMILY
WIDTH = 1000
HEIGHT = 680
DPI = 140
BACKGROUND = "#f6f7f9"
PANEL = "#ffffff"
GRID = "#d8dee7"
AXIS = "#66717f"
TEXT = "#18202a"
MUTED = "#66717f"
QPSK_COLOR = "#0f766e"
QDPSK_COLOR = "#2563eb"
ALT_COLOR = "#b45309"


def render_constellation_png(
    output_path: str | Path,
    symbols: np.ndarray,
    title: str,
    subtitle: str,
    max_points: int = 6000,
) -> Path:
    arr = _complex_array(symbols)
    if arr.size == 0:
        raise ValueError("symbols cannot be empty")
    points = arr[: int(max_points)]
    lim = _expanded_limit(points)
    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("同相分量 I", "正交分量 Q")
    canvas.cartesian_grid(-lim, lim, -lim, lim)
    canvas.scatter(points.real, points.imag, -lim, lim, -lim, lim, QPSK_COLOR)
    return canvas.save(output_path)


def render_diff_constellation_png(
    output_path: str | Path,
    symbols: np.ndarray,
    title: str,
    subtitle: str,
    max_points: int = 6000,
) -> Path:
    arr = _complex_array(symbols)
    if arr.size < 2:
        raise ValueError("symbols must contain at least two points")
    diff = arr[1:] * np.conjugate(arr[:-1])
    points = diff[: int(max_points)]
    lim = _expanded_limit(points)
    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("差分同相分量 I", "差分正交分量 Q")
    canvas.cartesian_grid(-lim, lim, -lim, lim)
    canvas.scatter(points.real, points.imag, -lim, lim, -lim, lim, QDPSK_COLOR)
    return canvas.save(output_path)


def render_eye_png(
    output_path: str | Path,
    samples: np.ndarray,
    sps: int,
    title: str,
    subtitle: str,
    traces: int = 120,
) -> Path:
    arr = _complex_array(samples)
    if arr.size < sps * 2:
        raise ValueError("not enough samples for an eye diagram")
    span = 2 * int(sps)
    usable = arr.size - span
    step = max(1, usable // max(1, traces))
    x = np.arange(span, dtype=np.float64) / float(sps)
    y_max = 2.0

    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("符号时间", "匹配滤波幅度")
    canvas.rect_grid(float(x[0]), float(x[-1]), 0.0, y_max)
    picked = 0
    for start in range(0, usable, step):
        window = arr[start : start + span]
        if window.size != span:
            break
        y = np.clip(np.abs(window), 0.0, y_max)
        canvas.line(x, y, float(x[0]), float(x[-1]), 0.0, y_max, QDPSK_COLOR, alpha=0.20, linewidth=0.7)
        picked += 1
        if picked >= traces:
            break
    return canvas.save(output_path)


def render_magnitude_png(
    output_path: str | Path,
    qpsk_samples: np.ndarray,
    qdpsk_samples: np.ndarray,
    title: str,
    subtitle: str,
    max_samples: int = 2400,
) -> Path:
    qpsk = np.abs(_complex_array(qpsk_samples)[: int(max_samples)])
    qdpsk = np.abs(_complex_array(qdpsk_samples)[: int(max_samples)])
    x = np.arange(min(qpsk.size, qdpsk.size), dtype=np.float64)
    qpsk = qpsk[: x.size]
    qdpsk = qdpsk[: x.size]
    ymax = _positive_limit(np.concatenate([qpsk, qdpsk]))
    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("样本序号", "幅度")
    canvas.rect_grid(float(x[0]), float(x[-1]), 0.0, ymax)
    canvas.line(x, qpsk, float(x[0]), float(x[-1]), 0.0, ymax, QPSK_COLOR, label="QPSK 幅度")
    canvas.line(x, qdpsk, float(x[0]), float(x[-1]), 0.0, ymax, QDPSK_COLOR, label="QDPSK 幅度")
    canvas.legend()
    return canvas.save(output_path)


def render_phase_png(
    output_path: str | Path,
    qpsk_symbols: np.ndarray,
    qdpsk_symbols: np.ndarray,
    title: str,
    subtitle: str,
    max_symbols: int = 1200,
) -> Path:
    qpsk = np.unwrap(np.angle(_complex_array(qpsk_symbols)[: int(max_symbols)]))
    qdpsk = np.unwrap(np.angle(_complex_array(qdpsk_symbols)[: int(max_symbols)]))
    x = np.arange(min(qpsk.size, qdpsk.size), dtype=np.float64)
    qpsk = qpsk[: x.size]
    qdpsk = qdpsk[: x.size]
    ymin, ymax = _range_limits(np.concatenate([qpsk, qdpsk]))
    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("符号序号", "展开相位 / rad")
    canvas.rect_grid(float(x[0]), float(x[-1]), ymin, ymax)
    canvas.line(x, qpsk, float(x[0]), float(x[-1]), ymin, ymax, QPSK_COLOR, label="QPSK 相位")
    canvas.line(x, qdpsk, float(x[0]), float(x[-1]), ymin, ymax, QDPSK_COLOR, label="QDPSK 相位")
    canvas.legend()
    return canvas.save(output_path)


def render_spectrum_png(
    output_path: str | Path,
    qpsk_samples: np.ndarray,
    qdpsk_samples: np.ndarray,
    title: str,
    subtitle: str,
    nfft: int = 8192,
) -> Path:
    qpsk_freq, qpsk_psd = _normalized_spectrum(qpsk_samples, nfft)
    qdpsk_freq, qdpsk_psd = _normalized_spectrum(qdpsk_samples, nfft)
    ymin, ymax = -80.0, 2.0
    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("归一化频率", "相对功率 / dB")
    canvas.rect_grid(-0.5, 0.5, ymin, ymax)
    canvas.line(qpsk_freq, np.clip(qpsk_psd, ymin, ymax), -0.5, 0.5, ymin, ymax, QPSK_COLOR, label="QPSK 功率谱")
    canvas.line(qdpsk_freq, np.clip(qdpsk_psd, ymin, ymax), -0.5, 0.5, ymin, ymax, QDPSK_COLOR, label="QDPSK 功率谱")
    canvas.legend()
    return canvas.save(output_path)


def render_evm_png(
    output_path: str | Path,
    qpsk_symbols: np.ndarray,
    qdpsk_symbols: np.ndarray,
    title: str,
    subtitle: str,
    max_symbols: int = 4000,
) -> Path:
    qpsk = _qpsk_error_magnitude(qpsk_symbols)[: int(max_symbols)]
    qdpsk = _qdpsk_diff_error_magnitude(qdpsk_symbols)[: int(max_symbols)]
    x = np.arange(min(qpsk.size, qdpsk.size), dtype=np.float64)
    qpsk = qpsk[: x.size]
    qdpsk = qdpsk[: x.size]
    ymax = _positive_limit(np.concatenate([qpsk, qdpsk]))
    canvas = _Canvas(title, subtitle)
    canvas.axes_labels("符号序号", "误差幅度")
    canvas.rect_grid(float(x[0]), float(x[-1]), 0.0, ymax)
    canvas.line(x, qpsk, float(x[0]), float(x[-1]), 0.0, ymax, QPSK_COLOR, label="QPSK 误差矢量")
    canvas.line(x, qdpsk, float(x[0]), float(x[-1]), 0.0, ymax, ALT_COLOR, label="QDPSK 差分误差矢量")
    canvas.legend()
    return canvas.save(output_path)


class _Canvas:
    def __init__(self, title: str, subtitle: str) -> None:
        self.fig = Figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI, frameon=False)
        self.canvas = FigureCanvasAgg(self.fig)
        self.fig.patch.set_facecolor(BACKGROUND)
        self.left = 110
        self.right = WIDTH - 56
        self.top = 112
        self.bottom = HEIGHT - 88
        self._legend_items: list[tuple[str, str]] = []
        self._fill_rect(0, 0, WIDTH, HEIGHT, BACKGROUND)
        self._fill_rect(self.left, self.top, self.right, self.bottom, PANEL)
        self._line(self.left, self.top, self.right, self.top, "#b7c0cc", linewidth=1.0)
        self._line(self.right, self.top, self.right, self.bottom, "#b7c0cc", linewidth=1.0)
        self._line(self.right, self.bottom, self.left, self.bottom, "#b7c0cc", linewidth=1.0)
        self._line(self.left, self.bottom, self.left, self.top, "#b7c0cc", linewidth=1.0)
        self._text(WIDTH / 2, 38, _normalize_title(title), 16, CHINESE_FONT, ha="center", va="center", color=TEXT)
        self._text(WIDTH / 2, 70, _normalize_subtitle(subtitle), 10, CHINESE_FONT, ha="center", va="center", color=MUTED)

    def axes_labels(self, x_label: str, y_label: str) -> None:
        self._text((self.left + self.right) / 2, HEIGHT - 38, x_label, 11, CHINESE_FONT, ha="center", va="center")
        self._text(34, (self.top + self.bottom) / 2, y_label, 11, CHINESE_FONT, ha="center", va="center", rotation=90)

    def cartesian_grid(self, xmin: float, xmax: float, ymin: float, ymax: float) -> None:
        self.rect_grid(xmin, xmax, ymin, ymax)
        x0 = self._map_x(0.0, xmin, xmax)
        y0 = self._map_y(0.0, ymin, ymax)
        self._line(self.left, y0, self.right, y0, AXIS, linewidth=1.0)
        self._line(x0, self.top, x0, self.bottom, AXIS, linewidth=1.0)

    def rect_grid(self, xmin: float, xmax: float, ymin: float, ymax: float) -> None:
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = self.left + frac * (self.right - self.left)
            y = self.top + frac * (self.bottom - self.top)
            self._line(x, self.top, x, self.bottom, GRID, linewidth=0.65)
            self._line(self.left, y, self.right, y, GRID, linewidth=0.65)
        for value in _ticks(xmin, xmax):
            x = self._map_x(value, xmin, xmax)
            self._text(x, self.bottom + 18, _fmt_tick(value), 9, LATIN_FONT, ha="center", va="center", color=MUTED)
        for value in _ticks(ymin, ymax):
            y = self._map_y(value, ymin, ymax)
            self._text(self.left - 14, y, _fmt_tick(value), 9, LATIN_FONT, ha="right", va="center", color=MUTED)

    def scatter(
        self,
        x: np.ndarray,
        y: np.ndarray,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        color: str,
    ) -> None:
        xs = self._map_x_arr(x, xmin, xmax)
        ys = self._map_y_arr(y, ymin, ymax)
        for px, py in zip(xs, ys):
            self._line(px - 1.5, py, px + 1.5, py, color, alpha=0.36, linewidth=1.1)

    def line(
        self,
        x: np.ndarray,
        y: np.ndarray,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        color: str,
        label: str | None = None,
        alpha: float = 0.90,
        linewidth: float = 1.15,
    ) -> None:
        if x.size == 0 or y.size == 0:
            return
        xs = self._map_x_arr(x, xmin, xmax)
        ys = self._map_y_arr(y, ymin, ymax)
        self.fig.lines.append(
            Line2D(xs, ys, color=color, alpha=alpha, linewidth=linewidth, transform=None)
        )
        if label:
            self._legend_items.append((label, color))

    def legend(self) -> None:
        if not self._legend_items:
            return
        x = self.right - 190
        y = self.top + 24
        self._fill_rect(x - 12, y - 18, x + 166, y + 26 * len(self._legend_items) - 6, PANEL)
        self._line(x - 12, y - 18, x + 166, y - 18, GRID, linewidth=0.8)
        self._line(x + 166, y - 18, x + 166, y + 26 * len(self._legend_items) - 6, GRID, linewidth=0.8)
        self._line(x + 166, y + 26 * len(self._legend_items) - 6, x - 12, y + 26 * len(self._legend_items) - 6, GRID, linewidth=0.8)
        self._line(x - 12, y + 26 * len(self._legend_items) - 6, x - 12, y - 18, GRID, linewidth=0.8)
        for index, (label, color) in enumerate(self._legend_items):
            yy = y + index * 26
            self._line(x, yy, x + 28, yy, color, linewidth=2.5)
            self._text(x + 38, yy, label, 10, CHINESE_FONT, ha="left", va="center", color=TEXT)

    def save(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.canvas.print_png(str(path))
        return path

    def _map_x(self, value: float, xmin: float, xmax: float) -> float:
        if xmax == xmin:
            return float(self.left)
        return self.left + (float(value) - xmin) * (self.right - self.left) / (xmax - xmin)

    def _map_y(self, value: float, ymin: float, ymax: float) -> float:
        if ymax == ymin:
            return float(self.bottom)
        return self.bottom - (float(value) - ymin) * (self.bottom - self.top) / (ymax - ymin)

    def _map_x_arr(self, values: np.ndarray, xmin: float, xmax: float) -> np.ndarray:
        if xmax == xmin:
            return np.full(values.shape, float(self.left), dtype=np.float64)
        return self.left + (values.astype(np.float64) - xmin) * (self.right - self.left) / (xmax - xmin)

    def _map_y_arr(self, values: np.ndarray, ymin: float, ymax: float) -> np.ndarray:
        if ymax == ymin:
            return np.full(values.shape, float(self.bottom), dtype=np.float64)
        return self.bottom - (values.astype(np.float64) - ymin) * (self.bottom - self.top) / (ymax - ymin)

    def _fill_rect(self, left: float, top: float, right: float, bottom: float, color: str) -> None:
        y = top
        step = 3.0
        while y <= bottom:
            self._line(left, y, right, y, color, linewidth=step + 0.5)
            y += step

    def _line(self, x0: float, y0: float, x1: float, y1: float, color: str, alpha: float = 1.0, linewidth: float = 1.0) -> None:
        self.fig.lines.append(
            Line2D([x0, x1], [y0, y1], color=color, alpha=alpha, linewidth=linewidth, transform=None)
        )

    def _text(
        self,
        x: float,
        y: float,
        text: str,
        size: int,
        family: str,
        ha: str,
        va: str,
        color: str = TEXT,
        rotation: float = 0.0,
    ) -> None:
        self.fig.text(
            x / WIDTH,
            1.0 - y / HEIGHT,
            text,
            fontsize=size,
            fontfamily=family,
            ha=ha,
            va=va,
            color=color,
            rotation=rotation,
        )


def _complex_array(values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.complex64)


def _expanded_limit(values: np.ndarray) -> float:
    real = values.real.astype(np.float64)
    imag = values.imag.astype(np.float64)
    limit = max(1.0, float(np.max(np.abs(np.concatenate([real, imag])))))
    return limit * 1.15


def _positive_limit(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 1.0
    return max(1.0, float(np.percentile(finite, 99.5))) * 1.12


def _range_limits(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return -1.0, 1.0
    low = float(np.percentile(finite, 1.0))
    high = float(np.percentile(finite, 99.0))
    if high <= low:
        return low - 1.0, high + 1.0
    pad = (high - low) * 0.08
    return low - pad, high + pad


def _normalized_spectrum(samples: np.ndarray, nfft: int) -> tuple[np.ndarray, np.ndarray]:
    arr = _complex_array(samples)
    if arr.size == 0:
        raise ValueError("samples cannot be empty")
    n = min(int(nfft), arr.size)
    window = np.hanning(n)
    segment = arr[:n] * window
    spectrum = np.fft.fftshift(np.fft.fft(segment, n=n))
    power = np.abs(spectrum) ** 2
    power_db = 10.0 * np.log10(power / max(float(power.max()), 1e-12) + 1e-12)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0))
    return freq, power_db


def _qpsk_error_magnitude(symbols: np.ndarray) -> np.ndarray:
    arr = _complex_array(symbols)
    if arr.size == 0:
        return np.asarray([], dtype=np.float64)
    ideal_real = np.where(arr.real >= 0.0, 1.0, -1.0)
    ideal_imag = np.where(arr.imag >= 0.0, 1.0, -1.0)
    ideals = ideal_real + 1j * ideal_imag
    return np.abs(arr - ideals).astype(np.float64)


def _qdpsk_diff_error_magnitude(symbols: np.ndarray) -> np.ndarray:
    arr = _complex_array(symbols)
    if arr.size < 2:
        return np.asarray([], dtype=np.float64)
    diff = arr[1:] * np.conjugate(arr[:-1])
    phases = np.array([0.0, np.pi / 2.0, np.pi, -np.pi / 2.0], dtype=np.float64)
    ideal = np.exp(1j * phases)
    nearest = ideal[np.argmin(np.abs(diff[:, None] - ideal[None, :]), axis=1)]
    return np.abs(diff - nearest).astype(np.float64)


def _ticks(vmin: float, vmax: float) -> list[float]:
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax == vmin:
        return [vmin]
    return [vmin + (vmax - vmin) * frac for frac in (0.0, 0.25, 0.5, 0.75, 1.0)]


def _fmt_tick(value: float) -> str:
    if abs(value) >= 1000.0:
        return "%.0f" % value
    if abs(value) >= 10.0:
        return "%.1f" % value
    return "%.2f" % value


def _normalize_title(title: str) -> str:
    mapping = {
        "QPSK RX CONSTELLATION": "QPSK 接收星座图",
        "QDPSK RX CONSTELLATION": "QDPSK 接收星座图",
        "QDPSK DIFF CONSTELLATION": "QDPSK 差分星座图",
        "QPSK RX EYE": "QPSK 接收眼图",
        "QDPSK RX EYE": "QDPSK 接收眼图",
        "RX MAGNITUDE": "接收波形幅度",
        "RX PHASE": "接收符号相位轨迹",
        "RX SPECTRUM": "接收信号功率谱",
        "RX EVM": "接收误差矢量幅度",
    }
    return mapping.get(title, title)


def _normalize_subtitle(subtitle: str) -> str:
    mapping = {
        "matched filter + fixed timing": "匹配滤波 + 固定定时抽样",
        "symbol[k] * conj(symbol[k-1])": "相邻符号差分：symbol[k] * conj(symbol[k-1])",
        "matched filter magnitude": "匹配滤波输出幅度",
        "matched filter IQ magnitude": "匹配滤波后 IQ 幅度",
        "fixed-timing symbol phase": "固定定时抽样后的符号相位",
        "matched filter IQ spectrum": "匹配滤波后 IQ 频谱",
        "nearest ideal decision error": "到最近理想判决点的误差幅度",
    }
    return mapping.get(subtitle, subtitle)
