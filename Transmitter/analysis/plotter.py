"""Matplotlib rendering for transmitter-side plot PNGs."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

LATIN_FONT = "Times New Roman"
CHINESE_FONT = "SimHei"
LATIN_PROP = FontProperties(family=LATIN_FONT)
CHINESE_PROP = FontProperties(family=CHINESE_FONT)

matplotlib.rcParams.update(
    {
        "font.family": LATIN_FONT,
        "font.serif": [LATIN_FONT],
        "font.sans-serif": [CHINESE_FONT, "Microsoft YaHei"],
        "axes.unicode_minus": False,
    }
)

import matplotlib.pyplot as plt
import numpy as np


def render_eye_png(eye_traces, output_path, sps, title):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    eye_traces = np.asarray(eye_traces, dtype=np.float64)
    fig, axis = plt.subplots(figsize=(9.0, 4.8), dpi=120)
    x_axis = np.arange(eye_traces.shape[1], dtype=np.float64) / float(sps)
    for trace in eye_traces:
        axis.plot(x_axis, trace, color="#0B6E4F", alpha=0.16, linewidth=0.8)
    _set_mixed_title(fig, title)
    _set_mixed_xlabel(fig, "时间（符号周期）")
    _set_mixed_ylabel(fig, "同相分量幅度")
    _set_tick_font(axis)
    axis.grid(True, alpha=0.28)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.84, bottom=0.18)
    fig.savefig(output)
    plt.close(fig)


def render_constellation_png(symbols, output_path, title):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    symbols = np.asarray(symbols, dtype=np.complex64)
    fig, axis = plt.subplots(figsize=(5.2, 5.2), dpi=120)
    axis.scatter(symbols.real, symbols.imag, s=4, color="#1D4ED8", alpha=0.36)
    axis.axhline(0.0, color="#444444", linewidth=0.8, alpha=0.55)
    axis.axvline(0.0, color="#444444", linewidth=0.8, alpha=0.55)
    _set_mixed_title(fig, title)
    _set_mixed_xlabel(fig, "同相分量 I")
    _set_mixed_ylabel(fig, "正交分量 Q")
    _set_tick_font(axis)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlim(-1.25, 1.25)
    axis.set_ylim(-1.25, 1.25)
    axis.grid(True, alpha=0.28)
    fig.subplots_adjust(left=0.16, right=0.96, top=0.84, bottom=0.16)
    fig.savefig(output)
    plt.close(fig)


def render_psd_png(freqs, psd_db, output_path, title):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    freqs = np.asarray(freqs, dtype=np.float64)
    psd_db = np.asarray(psd_db, dtype=np.float64)
    fig, axis = plt.subplots(figsize=(9.0, 4.8), dpi=120)
    axis.plot(freqs, psd_db, color="#B45309", linewidth=1.2)
    _set_mixed_title(fig, title)
    _set_mixed_xlabel(fig, "归一化频率")
    _set_mixed_ylabel(fig, "功率谱密度（dB，归一化）")
    _set_tick_font(axis)
    axis.set_ylim(-90, 5)
    axis.grid(True, alpha=0.28)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.84, bottom=0.18)
    fig.savefig(output)
    plt.close(fig)


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
    filename_prefix="",
):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    prefix = ("%s_" % filename_prefix) if filename_prefix else ""
    eye_path = output / ("%seye.png" % prefix)
    constellation_path = output / ("%sconstellation.png" % prefix)
    psd_path = output / ("%spsd.png" % prefix)

    render_eye_png(
        eye_traces,
        eye_path,
        sps=sps,
        title="%s 发端信道前基带眼图" % channel_name,
    )
    render_constellation_png(
        constellation_points,
        constellation_path,
        title="%s 发端信道前星座图" % channel_name,
    )
    render_psd_png(
        freqs,
        psd_db,
        psd_path,
        title="%s 发端信道前基带功率谱" % channel_name,
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


def _set_mixed_title(fig, title: str) -> None:
    _mixed_fig_text(fig, 0.5, 0.94, title, size=13, ha="center", va="top")


def _set_mixed_xlabel(fig, label: str) -> None:
    _mixed_fig_text(fig, 0.5, 0.055, label, size=11, ha="center", va="bottom")


def _set_mixed_ylabel(fig, label: str) -> None:
    _mixed_fig_text(fig, 0.025, 0.5, label, size=11, ha="center", va="center", rotation=90)


def _set_tick_font(axis) -> None:
    for tick in axis.get_xticklabels() + axis.get_yticklabels():
        tick.set_fontproperties(LATIN_PROP)


def _mixed_fig_text(
    fig,
    x: float,
    y: float,
    text: str,
    size: int,
    ha: str,
    va: str,
    rotation: float = 0.0,
) -> None:
    runs = _font_runs(str(text))
    if not runs:
        return
    if rotation:
        _mixed_rotated_fig_text(fig, x, y, runs, size, ha, va, rotation)
        return

    widths = [_text_width(run, size, prop) / fig.get_figwidth() for run, prop in runs]
    total = sum(widths)
    if ha == "center":
        cursor = x - total / 2.0
    elif ha == "right":
        cursor = x - total
    else:
        cursor = x
    for (run, prop), width in zip(runs, widths):
        fig.text(
            cursor,
            y,
            run,
            fontproperties=prop,
            fontsize=size,
            ha="left",
            va=va,
            rotation=rotation,
        )
        cursor += width


def _mixed_rotated_fig_text(fig, x, y, runs, size, ha, va, rotation) -> None:
    widths = [_text_width(run, size, prop) / fig.get_figheight() for run, prop in runs]
    total = sum(widths)
    if ha == "center":
        cursor = y - total / 2.0
    elif ha == "right":
        cursor = y - total
    else:
        cursor = y
    for (run, prop), width in zip(runs, widths):
        fig.text(
            x,
            cursor,
            run,
            fontproperties=prop,
            fontsize=size,
            ha="left",
            va=va,
            rotation=rotation,
        )
        cursor += width


def _font_runs(text: str):
    runs = []
    current = []
    current_prop = None
    for char in text:
        prop = LATIN_PROP if _is_latin_char(char) else CHINESE_PROP
        if current_prop is None:
            current_prop = prop
        if prop is not current_prop:
            runs.append(("".join(current), current_prop))
            current = [char]
            current_prop = prop
        else:
            current.append(char)
    if current:
        runs.append(("".join(current), current_prop or LATIN_PROP))
    return runs


def _is_latin_char(char: str) -> bool:
    return ord(char) <= 0x024F


def _text_width(text: str, size: int, prop: FontProperties) -> float:
    if not text:
        return 0.0
    path = TextPath((0, 0), text, size=size, prop=prop)
    return float(path.get_extents().width) / 72.0
