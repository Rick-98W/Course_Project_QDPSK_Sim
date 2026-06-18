"""Reusable transmitter DSP, plotting, and UDP-send pipeline."""

from __future__ import annotations

from datetime import datetime

import numpy as np

import config
from analysis.analysis import compute_eye_traces, compute_psd, sample_constellation
from analysis.plotter import render_all_tx_plots, render_constellation_png, render_eye_png
from core.bitstream import bits_to_bytes, bytes_to_bits
from core.channel import apply_channel, channel_summary
from core.image_source import build_image_frame, load_source_image
from core.modulation import (
    average_power,
    filter_delay_samples,
    qdpsk_modulate,
    qpsk_modulate,
    pulse_shape,
    rrc_filter,
    unique_constellation_points,
)
from core.packet import CHANNEL_QDPSK, CHANNEL_QPSK, fragment_iq_stream
from core.preview_dump import write_packet_preview
from core.udp_sender import send_packets


def run_transmitter_pipeline(
    snr_db=None,
    phase_deg=None,
    target_host=None,
    target_port=None,
    send_udp=False,
    image_path=None,
    include_channel_plots=True,
):
    """Run one complete transmitter pass.

    The transmitter-side diagnostic plots are always rendered from clean
    transmit signals. Channel-impaired IQ is only used for UDP payloads.
    """
    snr_db = config.SNR_DB if snr_db is None else float(snr_db)
    phase_deg = config.PHASE_DEG if phase_deg is None else float(phase_deg)
    target_host = config.TARGET_HOST if target_host is None else str(target_host)
    target_port = config.TARGET_PORT if target_port is None else int(target_port)

    source = load_source_image(config.IMAGE_PATH if image_path is None else image_path)
    frame = build_image_frame(source)
    bits = bytes_to_bits(frame)
    roundtrip = bits_to_bytes(bits)

    qpsk_symbols = qpsk_modulate(bits)
    qdpsk_symbols = qdpsk_modulate(bits)
    rrc_taps = rrc_filter(
        beta=config.RRC_BETA,
        sps=config.SAMPLES_PER_SYMBOL,
        span=config.RRC_SPAN,
    )
    qpsk_waveform = pulse_shape(qpsk_symbols, rrc_taps, config.SAMPLES_PER_SYMBOL)
    qdpsk_waveform = pulse_shape(qdpsk_symbols, rrc_taps, config.SAMPLES_PER_SYMBOL)

    rng = np.random.default_rng(config.RANDOM_SEED)
    qpsk_impaired = apply_channel(qpsk_waveform, snr_db, phase_deg, rng)
    qdpsk_impaired = apply_channel(qdpsk_waveform, snr_db, phase_deg, rng)
    qpsk_impaired_points = np.asarray([], dtype=np.complex64)
    qdpsk_impaired_points = np.asarray([], dtype=np.complex64)
    qpsk_impaired_eye_traces = np.asarray([], dtype=np.float64).reshape(0, 0)
    qdpsk_impaired_eye_traces = np.asarray([], dtype=np.float64).reshape(0, 0)

    plot_specs = {
        "QPSK": {
            "symbols": qpsk_symbols,
            "waveform": qpsk_waveform,
        },
        "QDPSK": {
            "symbols": qdpsk_symbols,
            "waveform": qdpsk_waveform,
        },
    }

    plot_outputs = {}
    for channel_name, spec in plot_specs.items():
        eye_traces = compute_eye_traces(
            spec["waveform"],
            sps=config.SAMPLES_PER_SYMBOL,
            traces=config.EYE_TRACES,
            span_symbols=config.EYE_SPAN_SYMBOLS,
        )
        constellation_points = sample_constellation(
            spec["symbols"],
            max_points=config.CONSTELLATION_MAX_POINTS,
        )
        freqs, psd_db = compute_psd(
            spec["waveform"],
            sample_rate=config.SAMPLE_RATE_HZ,
            nfft=config.PSD_NFFT,
        )
        plot_outputs[channel_name] = {
            "paths": render_all_tx_plots(
                symbols=spec["symbols"],
                waveform=spec["waveform"],
                output_dir=config.GENERATED_DIR,
                sps=config.SAMPLES_PER_SYMBOL,
                eye_traces=eye_traces,
                eye_span_symbols=config.EYE_SPAN_SYMBOLS,
                constellation_points=constellation_points,
                freqs=freqs,
                psd_db=psd_db,
                channel_name=channel_name,
                filename_prefix=channel_name.lower(),
            ),
            "eye_trace_count": int(eye_traces.shape[0]),
            "constellation_plotted_points": int(constellation_points.size),
            "psd_bins": int(psd_db.size),
        }

    qpsk_impaired_constellation_path = (
        config.GENERATED_DIR / "qpsk_impaired_constellation.png"
    )
    qdpsk_impaired_constellation_path = (
        config.GENERATED_DIR / "qdpsk_impaired_constellation.png"
    )
    qpsk_impaired_eye_path = config.GENERATED_DIR / "qpsk_impaired_eye.png"
    qdpsk_impaired_eye_path = config.GENERATED_DIR / "qdpsk_impaired_eye.png"
    if include_channel_plots or send_udp:
        qpsk_impaired_points = sample_constellation(
            qpsk_impaired,
            max_points=config.CONSTELLATION_MAX_POINTS,
        )
        qdpsk_impaired_points = sample_constellation(
            qdpsk_impaired,
            max_points=config.CONSTELLATION_MAX_POINTS,
        )
        qpsk_impaired_eye_traces = compute_eye_traces(
            qpsk_impaired,
            sps=config.SAMPLES_PER_SYMBOL,
            traces=config.EYE_TRACES,
            span_symbols=config.EYE_SPAN_SYMBOLS,
        )
        qdpsk_impaired_eye_traces = compute_eye_traces(
            qdpsk_impaired,
            sps=config.SAMPLES_PER_SYMBOL,
            traces=config.EYE_TRACES,
            span_symbols=config.EYE_SPAN_SYMBOLS,
        )
        render_constellation_png(
            qpsk_impaired_points,
            qpsk_impaired_constellation_path,
            "QPSK 信道后采样星座图",
        )
        render_constellation_png(
            qdpsk_impaired_points,
            qdpsk_impaired_constellation_path,
            "QDPSK 信道后采样星座图",
        )
        render_eye_png(
            qpsk_impaired_eye_traces,
            qpsk_impaired_eye_path,
            sps=config.SAMPLES_PER_SYMBOL,
            title="QPSK 信道后基带眼图",
        )
        render_eye_png(
            qdpsk_impaired_eye_traces,
            qdpsk_impaired_eye_path,
            sps=config.SAMPLES_PER_SYMBOL,
            title="QDPSK 信道后基带眼图",
        )

    frame_id = int(np.random.default_rng(config.RANDOM_SEED).integers(0, 2**32 - 1))
    qpsk_packets = fragment_iq_stream(
        qpsk_impaired,
        frame_id=frame_id,
        channel_id=CHANNEL_QPSK,
        max_payload_bytes=config.UDP_FRAGMENT_PAYLOAD_BYTES,
    )
    qdpsk_packets = fragment_iq_stream(
        qdpsk_impaired,
        frame_id=frame_id,
        channel_id=CHANNEL_QDPSK,
        max_payload_bytes=config.UDP_FRAGMENT_PAYLOAD_BYTES,
    )
    qpsk_preview_path = write_packet_preview(
        config.GENERATED_DIR / "qpsk_packet_preview.txt",
        qpsk_packets[0],
        "QPSK",
    )
    qdpsk_preview_path = write_packet_preview(
        config.GENERATED_DIR / "qdpsk_packet_preview.txt",
        qdpsk_packets[0],
        "QDPSK",
    )

    tx_result = {
        "packet_count": 0,
        "total_bytes": 0,
        "elapsed_sec": 0.0,
        "bytes_per_sec": 0.0,
        "sent": False,
    }
    if send_udp:
        tx_result = send_packets(
            qpsk_packets + qdpsk_packets,
            host=target_host,
            port=target_port,
            delay_sec=config.UDP_INTER_PACKET_DELAY_SEC,
        )
        tx_result["sent"] = True

    qpsk_stats = channel_summary(qpsk_waveform, qpsk_impaired)
    qdpsk_stats = channel_summary(qdpsk_waveform, qdpsk_impaired)

    qpsk_unique_points = unique_constellation_points(qpsk_symbols)
    qdpsk_unique_points = unique_constellation_points(qdpsk_symbols)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": {
            "host": target_host,
            "port": int(target_port),
        },
        "image": {
            "path": str(source.path),
            "width": int(source.width),
            "height": int(source.height),
            "channels": int(source.channels),
            "payload_bytes": int(source.payload_bytes),
            "frame_bytes": int(len(frame)),
            "bit_count": int(bits.size),
            "frame_magic": repr(frame[:4]),
            "roundtrip_bytes_match": bool(roundtrip == frame),
        },
        "modulation": {
            "qpsk_symbol_count": int(qpsk_symbols.size),
            "qdpsk_symbol_count": int(qdpsk_symbols.size),
            "qpsk_average_power": float(average_power(qpsk_symbols)),
            "qdpsk_average_power": float(average_power(qdpsk_symbols)),
            "qpsk_unique_constellation_points": _format_complex_points(qpsk_unique_points),
            "qdpsk_unique_constellation_points": _format_complex_points(qdpsk_unique_points),
        },
        "rrc": {
            "beta": float(config.RRC_BETA),
            "span_symbols": int(config.RRC_SPAN),
            "samples_per_symbol": int(config.SAMPLES_PER_SYMBOL),
            "tap_count": int(rrc_taps.size),
            "tap_energy": float((rrc_taps**2).sum()),
            "filter_delay_samples": int(filter_delay_samples(rrc_taps)),
            "qpsk_waveform_sample_count": int(qpsk_waveform.size),
            "qdpsk_waveform_sample_count": int(qdpsk_waveform.size),
            "qpsk_waveform_average_power": float(average_power(qpsk_waveform)),
            "qdpsk_waveform_average_power": float(average_power(qdpsk_waveform)),
        },
        "channel": {
            "snr_db": float(snr_db),
            "phase_deg": float(phase_deg),
            "qpsk_impaired_power": float(qpsk_stats["impaired_power"]),
            "qdpsk_impaired_power": float(qdpsk_stats["impaired_power"]),
            "qpsk_estimated_snr_db": float(qpsk_stats["estimated_snr_db"]),
            "qdpsk_estimated_snr_db": float(qdpsk_stats["estimated_snr_db"]),
        },
        "plots": {
            "qpsk": {
                "eye": plot_outputs["QPSK"]["paths"]["eye"],
                "constellation": plot_outputs["QPSK"]["paths"]["constellation"],
                "psd": plot_outputs["QPSK"]["paths"]["psd"],
                "impaired_constellation": str(qpsk_impaired_constellation_path),
                "impaired_eye": str(qpsk_impaired_eye_path),
                "eye_trace_count": plot_outputs["QPSK"]["eye_trace_count"],
                "impaired_eye_trace_count": int(qpsk_impaired_eye_traces.shape[0]),
                "constellation_plotted_points": plot_outputs["QPSK"]["constellation_plotted_points"],
                "impaired_constellation_points": int(qpsk_impaired_points.size),
                "psd_bins": plot_outputs["QPSK"]["psd_bins"],
            },
            "qdpsk": {
                "eye": plot_outputs["QDPSK"]["paths"]["eye"],
                "constellation": plot_outputs["QDPSK"]["paths"]["constellation"],
                "psd": plot_outputs["QDPSK"]["paths"]["psd"],
                "impaired_constellation": str(qdpsk_impaired_constellation_path),
                "impaired_eye": str(qdpsk_impaired_eye_path),
                "eye_trace_count": plot_outputs["QDPSK"]["eye_trace_count"],
                "impaired_eye_trace_count": int(qdpsk_impaired_eye_traces.shape[0]),
                "constellation_plotted_points": plot_outputs["QDPSK"]["constellation_plotted_points"],
                "impaired_constellation_points": int(qdpsk_impaired_points.size),
                "psd_bins": plot_outputs["QDPSK"]["psd_bins"],
            },
        },
        "udp": {
            "frame_id": int(frame_id),
            "qpsk_packet_count": int(len(qpsk_packets)),
            "qdpsk_packet_count": int(len(qdpsk_packets)),
            "qpsk_first_packet_bytes": int(len(qpsk_packets[0])) if qpsk_packets else 0,
            "qdpsk_first_packet_bytes": int(len(qdpsk_packets[0])) if qdpsk_packets else 0,
            "qpsk_preview_file": str(qpsk_preview_path),
            "qdpsk_preview_file": str(qdpsk_preview_path),
            "send_result": tx_result,
        },
    }


def print_pipeline_summary(result):
    """Print the concise diagnostic summary expected by the current logs."""
    print("Transmitter round 8: dual-channel HTML control page")
    print("image path: %s" % result["image"]["path"])
    print(
        "image size: %dx%d"
        % (result["image"]["width"], result["image"]["height"])
    )
    print("target: %s:%d" % (result["target"]["host"], result["target"]["port"]))
    print("SNR target dB: %.3f" % result["channel"]["snr_db"])
    print("phase offset deg: %.3f" % result["channel"]["phase_deg"])
    print(
        "QPSK stats: packets=%d, estimated_snr_db=%.3f"
        % (
            result["udp"]["qpsk_packet_count"],
            result["channel"]["qpsk_estimated_snr_db"],
        )
    )
    print(
        "QDPSK stats: packets=%d, estimated_snr_db=%.3f"
        % (
            result["udp"]["qdpsk_packet_count"],
            result["channel"]["qdpsk_estimated_snr_db"],
        )
    )
    print("QPSK estimated SNR dB: %.3f" % result["channel"]["qpsk_estimated_snr_db"])
    print("QDPSK estimated SNR dB: %.3f" % result["channel"]["qdpsk_estimated_snr_db"])
    print("QPSK eye PNG: %s" % result["plots"]["qpsk"]["eye"])
    print("QPSK constellation PNG: %s" % result["plots"]["qpsk"]["constellation"])
    print("QPSK PSD PNG: %s" % result["plots"]["qpsk"]["psd"])
    print(
        "QPSK impaired constellation PNG: %s"
        % result["plots"]["qpsk"]["impaired_constellation"]
    )
    print("QPSK impaired eye PNG: %s" % result["plots"]["qpsk"]["impaired_eye"])
    print("QDPSK eye PNG: %s" % result["plots"]["qdpsk"]["eye"])
    print("QDPSK constellation PNG: %s" % result["plots"]["qdpsk"]["constellation"])
    print("QDPSK PSD PNG: %s" % result["plots"]["qdpsk"]["psd"])
    print(
        "QDPSK impaired constellation PNG: %s"
        % result["plots"]["qdpsk"]["impaired_constellation"]
    )
    print("QDPSK impaired eye PNG: %s" % result["plots"]["qdpsk"]["impaired_eye"])


def _format_complex_points(points):
    return [
        "%.6f%+.6fj" % (float(point.real), float(point.imag))
        for point in np.asarray(points)
    ]
