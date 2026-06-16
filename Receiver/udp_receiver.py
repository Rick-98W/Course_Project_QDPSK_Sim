"""UDP receive loop for Receiver."""

from __future__ import annotations

import socket
import time
from pathlib import Path
from threading import Event
from typing import Callable

import numpy as np

import config
from capture import capture_frame, format_capture_outputs
from frame_buffer import FrameBuffer
from packet import (
    CHANNEL_NAMES,
    HEADER_SIZE,
    PacketError,
    format_header,
    parse_fragment,
)


def average_power(iq: np.ndarray) -> float:
    if iq.size == 0:
        return 0.0
    return float(np.mean(np.abs(iq) ** 2))


def print_iq_summary(frame_id: int, channels: dict[int, np.ndarray]) -> None:
    print("[FRAME COMPLETE] frame_id=%d" % frame_id)
    for channel_id in sorted(channels):
        iq = channels[channel_id]
        channel_name = CHANNEL_NAMES.get(channel_id, "UNKNOWN")
        print(
            "%s dtype: %s | sample count: %d | average power: %.6f"
            % (channel_name, iq.dtype, len(iq), average_power(iq))
        )

        if len(iq) != config.EXPECTED_TOTAL_SAMPLES:
            print(
                "[WARN] %s sample count expected %d, got %d"
                % (channel_name, config.EXPECTED_TOTAL_SAMPLES, len(iq))
            )


def _print_idle_report(pending: list) -> None:
    if pending:
        print("[IDLE] waiting for complete frame fragments...")
        for channel_frame in pending[:4]:
            print("[IDLE] %s" % channel_frame.progress_line())
    else:
        print("[IDLE] waiting for first UDP fragments...")


def run_receiver(
    listen_host: str = config.LISTEN_HOST,
    listen_port: int = config.LISTEN_PORT,
    stop_after_complete_frame: bool = False,
    save_completed_frames: bool | None = None,
    on_progress: Callable[[object], None] | None = None,
    on_idle: Callable[[list], None] | None = None,
    on_first_datagram: Callable[[bytes, tuple[str, int]], None] | None = None,
    on_first_header: Callable[[object], None] | None = None,
    on_frame_complete: Callable[[int, dict[int, np.ndarray], dict[int, Path]], None] | None = None,
    stop_event: Event | None = None,
) -> None:
    frame_buffer = FrameBuffer(expected_channels=config.EXPECTED_CHANNELS)
    first_header_printed = False
    invalid_packets = 0
    received_packets = 0
    should_save_completed_frames = (
        config.SAVE_COMPLETED_FRAMES
        if save_completed_frames is None
        else save_completed_frames
    )
    started_at = time.monotonic()
    last_packet_at = started_at
    last_idle_report_at = started_at

    print("QDPSK Receiver UDP listener")
    print("listen: %s:%d" % (listen_host, listen_port))
    print("header size: %d bytes" % HEADER_SIZE)
    print("expected sample format: complex64")
    print("waiting for UDP fragments...")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((listen_host, int(listen_port)))
        sock.settimeout(config.SOCKET_TIMEOUT_SEC)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, int(config.SOCKET_RCVBUF_BYTES))

        while True:
            if stop_event is not None and stop_event.is_set():
                break
            try:
                datagram, address = sock.recvfrom(config.MAX_DATAGRAM_BYTES)
            except socket.timeout:
                now = time.monotonic()
                if now - last_packet_at >= config.IDLE_DIAGNOSTIC_SEC and now - last_idle_report_at >= config.IDLE_DIAGNOSTIC_SEC:
                    pending = frame_buffer.pending_frames()
                    if on_idle is None:
                        _print_idle_report(pending)
                    else:
                        on_idle(pending)
                    last_idle_report_at = now
                continue
            except KeyboardInterrupt:
                print("\n[STOP] keyboard interrupt")
                break

            last_packet_at = time.monotonic()
            received_packets += 1
            if received_packets == 1:
                if on_first_datagram is not None:
                    on_first_datagram(datagram, address)
                print(
                    "[FIRST DATAGRAM] from=%s:%d bytes=%d head=%s"
                    % (address[0], address[1], len(datagram), datagram[:12].hex())
                )

            try:
                header, payload = parse_fragment(datagram)
            except PacketError as exc:
                invalid_packets += 1
                print("[DROP] invalid packet from %s:%d: %s" % (address[0], address[1], exc))
                continue

            if not first_header_printed:
                if on_first_header is not None:
                    on_first_header(header)
                print("[FIRST HEADER] %s" % format_header(header))
                first_header_printed = True

            try:
                channel_frame, is_new = frame_buffer.add_fragment(header, payload)
            except PacketError as exc:
                invalid_packets += 1
                print("[DROP] frame conflict: %s" % exc)
                continue

            if is_new and channel_frame.should_report_progress(
                config.PROGRESS_CHUNK_STEP, config.PROGRESS_PERCENT_STEP
            ):
                print("[PROGRESS] %s" % channel_frame.progress_line())
                if on_progress is not None:
                    on_progress(channel_frame)
                channel_frame.mark_reported()

            if frame_buffer.frame_complete(header.frame_id):
                channels = frame_buffer.get_completed_frame(header.frame_id)
                print_iq_summary(header.frame_id, channels)
                outputs: dict[int, Path] = {}
                if should_save_completed_frames:
                    outputs = capture_frame(header.frame_id, channels, config.CAPTURE_DIR)
                    print("[CAPTURE] %s" % format_capture_outputs(outputs))
                if on_frame_complete is not None:
                    on_frame_complete(header.frame_id, channels, outputs)
                frame_buffer.drop_frame(header.frame_id)
                if stop_after_complete_frame:
                    break

    elapsed = time.monotonic() - started_at
    print(
        "[SUMMARY] packets=%d invalid=%d elapsed_sec=%.3f"
        % (received_packets, invalid_packets, elapsed)
    )
