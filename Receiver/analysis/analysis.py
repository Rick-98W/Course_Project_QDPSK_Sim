"""Offline receiver capture analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

import config
from analysis.dsp import average_power, constellation_points, fixed_symbol_sample, matched_filter, rrc_filter
from analysis.demodulation import bits_to_bytes, demodulate_symbols
from analysis.image_output import compute_mse_psnr, write_png_rgb
from analysis.image_recovery import recover_image_lenient
from analysis.plotter import (
    render_constellation_png,
    render_diff_constellation_png,
    render_evm_png,
    render_eye_png,
    render_magnitude_png,
    render_phase_png,
    render_spectrum_png,
)
from analysis.reference_image import load_reference_image
from analysis.report import (
    ChannelReport,
    PlotReport,
    write_capture_index,
    write_capture_report,
    write_capture_summary,
)
from core.packet import CHANNEL_QDPSK, CHANNEL_QPSK


@dataclass(frozen=True)
class CaptureAnalysisResult:
    channel_name: str
    sample_count: int
    raw_average_power: float
    filtered_samples: np.ndarray
    filtered_sample_count: int
    filtered_average_power: float
    symbol_sample_count: int
    symbol_average_power: float
    constellation_points: np.ndarray
    raw_symbols: np.ndarray


@dataclass(frozen=True)
class CaptureAnalysisBundle:
    capture_dir: Path
    qpsk_path: Path
    qdpsk_path: Path
    qpsk_capture: CaptureAnalysisResult
    qdpsk_capture: CaptureAnalysisResult
    qpsk_bits: np.ndarray
    qdpsk_bits: np.ndarray
    qpsk_payload: bytes
    qdpsk_payload: bytes
    qpsk_report: ChannelReport
    qdpsk_report: ChannelReport
    plots: tuple[PlotReport, ...]
    report_path: Path
    summary_path: Path
    latest_report_path: Path
    index_path: Path


def analyze_capture_file(
    path: str | Path,
    channel_name: str,
    sample_offset: int = 0,
) -> CaptureAnalysisResult:
    """Load a completed IQ capture and run fixed-timing matched filtering."""
    iq = np.load(Path(path))
    taps = rrc_filter(config.RRC_BETA, config.SAMPLES_PER_SYMBOL, config.RRC_SPAN)
    filtered = matched_filter(iq, taps)
    symbol_start = 2 * ((taps.size - 1) // 2)
    symbols = fixed_symbol_sample(
        filtered,
        sps=config.SAMPLES_PER_SYMBOL,
        filter_delay_samples=symbol_start,
        sample_offset=sample_offset,
    )
    return CaptureAnalysisResult(
        channel_name=channel_name,
        sample_count=int(iq.size),
        raw_average_power=average_power(iq),
        filtered_samples=filtered,
        filtered_sample_count=int(filtered.size),
        filtered_average_power=average_power(filtered),
        symbol_sample_count=int(symbols.size),
        symbol_average_power=average_power(symbols),
        constellation_points=constellation_points(
            symbols, limit=config.CONSTELLATION_MAX_POINTS
        ),
        raw_symbols=symbols,
    )


def summarize_capture_result(result: CaptureAnalysisResult) -> str:
    """Format a compact analysis summary."""
    return (
        "%s raw=%d power=%.6f filtered=%d filtered_power=%.6f symbols=%d symbol_power=%.6f"
        % (
            result.channel_name,
            result.sample_count,
            result.raw_average_power,
            result.filtered_sample_count,
            result.filtered_average_power,
            result.symbol_sample_count,
            result.symbol_average_power,
        )
    )


def latest_complete_capture_dir(capture_root: Path) -> Path:
    candidates = []
    for directory in Path(capture_root).glob("frame_*"):
        if directory.is_dir() and (directory / "qpsk.npy").exists() and (
            directory / "qdpsk.npy"
        ).exists():
            candidates.append(directory)
    if not candidates:
        raise FileNotFoundError("no complete capture directory found")
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def analyze_capture_directory(capture_dir: str | Path) -> CaptureAnalysisBundle:
    capture_dir = Path(capture_dir)
    qpsk_path = capture_dir / "qpsk.npy"
    qdpsk_path = capture_dir / "qdpsk.npy"

    qpsk_capture, qpsk_bits, qpsk_payload = _analyze_channel(
        qpsk_path, CHANNEL_QPSK, "QPSK"
    )
    qdpsk_capture, qdpsk_bits, qdpsk_payload = _analyze_channel(
        qdpsk_path, CHANNEL_QDPSK, "QDPSK"
    )

    print(summarize_capture_result(qpsk_capture))
    print(summarize_capture_result(qdpsk_capture))
    print("QPSK bits: %d | image bytes used: %d" % (qpsk_bits.size, len(qpsk_payload)))
    print(
        "QDPSK bits: %d | image bytes used: %d"
        % (qdpsk_bits.size, len(qdpsk_payload))
    )

    if not config.REFERENCE_IMAGE_PATH.is_file():
        raise FileNotFoundError(
            "reference image has not been uploaded by Transmitter: %s"
            % config.REFERENCE_IMAGE_PATH
        )
    reference = load_reference_image(config.REFERENCE_IMAGE_PATH)
    qpsk_report = _output_recovered_channel(
        "QPSK", qpsk_path, qpsk_capture, qpsk_payload, reference
    )
    qdpsk_report = _output_recovered_channel(
        "QDPSK", qdpsk_path, qdpsk_capture, qdpsk_payload, reference
    )
    plots = _output_capture_plots(capture_dir, qpsk_capture, qdpsk_capture)
    report_path = write_capture_report(
        capture_dir / "capture_report.html",
        config.REFERENCE_IMAGE_PATH,
        qpsk_report,
        qdpsk_report,
        plots,
    )
    summary_path = write_capture_summary(
        capture_dir / "capture_summary.json",
        config.REFERENCE_IMAGE_PATH,
        qpsk_report,
        qdpsk_report,
        report_path,
    )
    latest_report_path = write_capture_report(
        config.REPORT_DIR / "latest_capture_report.html",
        config.REFERENCE_IMAGE_PATH,
        qpsk_report,
        qdpsk_report,
        plots,
    )
    index_path = write_capture_index(
        config.REPORT_DIR / "index.html",
        config.BASE_DIR / "captures",
    )
    print("Capture report: %s" % report_path)
    print("Capture summary: %s" % summary_path)
    print("Latest report: %s" % latest_report_path)
    print("Report index: %s" % index_path)
    print("QPSK capture: %s" % qpsk_path)
    print("QDPSK capture: %s" % qdpsk_path)
    return CaptureAnalysisBundle(
        capture_dir=capture_dir,
        qpsk_path=qpsk_path,
        qdpsk_path=qdpsk_path,
        qpsk_capture=qpsk_capture,
        qdpsk_capture=qdpsk_capture,
        qpsk_bits=qpsk_bits,
        qdpsk_bits=qdpsk_bits,
        qpsk_payload=qpsk_payload,
        qdpsk_payload=qdpsk_payload,
        qpsk_report=qpsk_report,
        qdpsk_report=qdpsk_report,
        plots=plots,
        report_path=report_path,
        summary_path=summary_path,
        latest_report_path=latest_report_path,
        index_path=index_path,
    )


def analyze_latest_capture(capture_root: str | Path | None = None) -> CaptureAnalysisBundle:
    root = Path(capture_root) if capture_root is not None else config.CAPTURE_DIR
    capture_dir = latest_complete_capture_dir(root)
    return analyze_capture_directory(capture_dir)


def _analyze_channel(path: Path, channel_id: int, channel_name: str):
    capture = analyze_capture_file(path, channel_name)
    bits = demodulate_symbols(capture.raw_symbols, channel_id)
    payload = bits_to_bytes(bits[: config.EXPECTED_IMAGE_BITS])
    return capture, bits, payload


def _output_recovered_channel(
    channel_name: str,
    capture_path: Path,
    capture,
    payload: bytes,
    reference,
) -> ChannelReport:
    image = recover_image_lenient(payload)
    output_png = write_png_rgb(
        capture_path.parent / ("%s_recovered.png" % channel_name.lower()),
        image.width,
        image.height,
        image.rgb_bytes,
    )
    mse, psnr = compute_mse_psnr(reference.rgb_bytes, image.rgb_bytes)
    print(
        "%s image: %dx%d channels=%d payload=%d header_valid=%s"
        % (
            channel_name,
            image.width,
            image.height,
            image.channels,
            image.payload_bytes,
            image.header_valid,
        )
    )
    print(
        "%s MSE=%.6f PSNR=%s"
        % (channel_name, mse, "inf" if psnr == float("inf") else "%.3f" % psnr)
    )
    print("%s recovered PNG: %s" % (channel_name, output_png))
    return ChannelReport(
        name=channel_name,
        capture_path=capture_path,
        recovered_png=output_png,
        sample_count=capture.sample_count,
        raw_average_power=capture.raw_average_power,
        filtered_sample_count=capture.filtered_sample_count,
        filtered_average_power=capture.filtered_average_power,
        symbol_sample_count=capture.symbol_sample_count,
        symbol_average_power=capture.symbol_average_power,
        width=image.width,
        height=image.height,
        channels=image.channels,
        payload_bytes=image.payload_bytes,
        header_valid=image.header_valid,
        mse=mse,
        psnr=psnr,
    )


def _output_capture_plots(
    capture_dir: Path, qpsk_capture, qdpsk_capture
) -> tuple[PlotReport, ...]:
    qpsk_constellation = render_constellation_png(
        capture_dir / "qpsk_rx_constellation.png",
        qpsk_capture.raw_symbols,
        "QPSK RX CONSTELLATION",
        "matched filter + fixed timing",
        max_points=config.CONSTELLATION_MAX_POINTS,
    )
    qdpsk_constellation = render_constellation_png(
        capture_dir / "qdpsk_rx_constellation.png",
        qdpsk_capture.raw_symbols,
        "QDPSK RX CONSTELLATION",
        "matched filter + fixed timing",
        max_points=config.CONSTELLATION_MAX_POINTS,
    )
    qdpsk_diff = render_diff_constellation_png(
        capture_dir / "qdpsk_diff_constellation.png",
        qdpsk_capture.raw_symbols,
        "QDPSK DIFF CONSTELLATION",
        "symbol[k] * conj(symbol[k-1])",
        max_points=config.CONSTELLATION_MAX_POINTS,
    )
    qpsk_eye = render_eye_png(
        capture_dir / "qpsk_rx_eye.png",
        qpsk_capture.filtered_samples,
        config.SAMPLES_PER_SYMBOL,
        "QPSK RX EYE",
        "matched filter magnitude",
    )
    qdpsk_eye = render_eye_png(
        capture_dir / "qdpsk_rx_eye.png",
        qdpsk_capture.filtered_samples,
        config.SAMPLES_PER_SYMBOL,
        "QDPSK RX EYE",
        "matched filter magnitude",
    )
    magnitude = render_magnitude_png(
        capture_dir / "rx_magnitude.png",
        qpsk_capture.filtered_samples,
        qdpsk_capture.filtered_samples,
        "RX MAGNITUDE",
        "matched filter IQ magnitude",
    )
    phase = render_phase_png(
        capture_dir / "rx_phase.png",
        qpsk_capture.raw_symbols,
        qdpsk_capture.raw_symbols,
        "RX PHASE",
        "fixed-timing symbol phase",
    )
    spectrum = render_spectrum_png(
        capture_dir / "rx_spectrum.png",
        qpsk_capture.filtered_samples,
        qdpsk_capture.filtered_samples,
        "RX SPECTRUM",
        "matched filter IQ spectrum",
    )
    evm = render_evm_png(
        capture_dir / "rx_evm.png",
        qpsk_capture.raw_symbols,
        qdpsk_capture.raw_symbols,
        "RX EVM",
        "nearest ideal decision error",
    )
    print("QPSK RX constellation: %s" % qpsk_constellation)
    print("QDPSK RX constellation: %s" % qdpsk_constellation)
    print("QDPSK differential constellation: %s" % qdpsk_diff)
    print("QPSK RX eye: %s" % qpsk_eye)
    print("QDPSK RX eye: %s" % qdpsk_eye)
    print("RX magnitude: %s" % magnitude)
    print("RX phase: %s" % phase)
    print("RX spectrum: %s" % spectrum)
    print("RX EVM: %s" % evm)
    return (
        PlotReport(
            "QPSK 接收星座图",
            "匹配滤波 + 固定定时抽样",
            qpsk_constellation,
        ),
        PlotReport(
            "QDPSK 接收星座图",
            "匹配滤波 + 固定定时抽样",
            qdpsk_constellation,
        ),
        PlotReport(
            "QDPSK 差分星座图",
            "相邻符号差分",
            qdpsk_diff,
        ),
        PlotReport("QPSK 接收眼图", "匹配滤波输出幅度", qpsk_eye),
        PlotReport("QDPSK 接收眼图", "匹配滤波输出幅度", qdpsk_eye),
        PlotReport("接收波形幅度", "匹配滤波后 QPSK / QDPSK 幅度对比", magnitude),
        PlotReport("接收相位轨迹", "固定定时抽样后的相位变化", phase),
        PlotReport("接收功率谱", "匹配滤波后归一化频谱", spectrum),
        PlotReport("误差矢量幅度", "到最近理想判决点的误差", evm),
    )
