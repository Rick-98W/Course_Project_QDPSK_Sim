"""Matplotlib rendering for transmitter-side plot PNGs."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["SimHei", "Microsoft YaHei"],
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
    axis.set_title(title)
    axis.set_xlabel("时间（符号周期）")
    axis.set_ylabel("同相分量幅度")
    axis.grid(True, alpha=0.28)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.14)
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
    axis.set_title(title)
    axis.set_xlabel("同相分量 I")
    axis.set_ylabel("正交分量 Q")
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlim(-1.25, 1.25)
    axis.set_ylim(-1.25, 1.25)
    axis.grid(True, alpha=0.28)
    fig.subplots_adjust(left=0.14, right=0.96, top=0.90, bottom=0.12)
    fig.savefig(output)
    plt.close(fig)


def render_psd_png(freqs, psd_db, output_path, title):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    freqs = np.asarray(freqs, dtype=np.float64)
    psd_db = np.asarray(psd_db, dtype=np.float64)
    fig, axis = plt.subplots(figsize=(9.0, 4.8), dpi=120)
    axis.plot(freqs, psd_db, color="#B45309", linewidth=1.2)
    axis.set_title(title)
    axis.set_xlabel("归一化频率")
    axis.set_ylabel("功率谱密度（dB，归一化）")
    axis.set_ylim(-90, 5)
    axis.grid(True, alpha=0.28)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.14)
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
        title="%s 发端干净基带眼图" % channel_name,
    )
    render_constellation_png(
        constellation_points,
        constellation_path,
        title="%s 发端干净星座图" % channel_name,
    )
    render_psd_png(
        freqs,
        psd_db,
        psd_path,
        title="%s 发端干净基带功率谱" % channel_name,
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
