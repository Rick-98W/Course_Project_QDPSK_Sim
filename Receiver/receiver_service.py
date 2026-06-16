"""Background Receiver service for future GUI and HTTP API use."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import threading
import time
import traceback

import numpy as np

import config
from analysis import CaptureAnalysisBundle, analyze_capture_directory
from packet import CHANNEL_NAMES, FragmentHeader, format_header
from udp_receiver import run_receiver


@dataclass
class ChannelProgressState:
    frame_id: int
    channel_id: int
    channel_name: str
    received_chunks: int
    chunk_count: int
    percent: float
    duplicate_chunks: int

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "received_chunks": self.received_chunks,
            "chunk_count": self.chunk_count,
            "percent": self.percent,
            "duplicate_chunks": self.duplicate_chunks,
        }


@dataclass
class ReceiverServiceState:
    status: str = "stopped"
    listen_host: str = config.LISTEN_HOST
    listen_port: int = config.LISTEN_PORT
    started_at: float | None = None
    stopped_at: float | None = None
    last_packet_at: float | None = None
    last_frame_completed_at: float | None = None
    last_analysis_completed_at: float | None = None
    latest_frame_id: int | None = None
    latest_capture_dir: str | None = None
    latest_report_path: str | None = None
    latest_summary_path: str | None = None
    latest_index_path: str | None = None
    latest_qpsk_mse: float | None = None
    latest_qpsk_psnr: str | None = None
    latest_qpsk_header_valid: bool | None = None
    latest_qdpsk_mse: float | None = None
    latest_qdpsk_psnr: str | None = None
    latest_qdpsk_header_valid: bool | None = None
    latest_assets: dict[str, str] = field(default_factory=dict)
    latest_channel_stats: dict[str, dict] = field(default_factory=dict)
    first_header: str | None = None
    last_error: str | None = None
    progress: dict[int, ChannelProgressState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "listen_host": self.listen_host,
            "listen_port": self.listen_port,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "last_packet_at": self.last_packet_at,
            "last_frame_completed_at": self.last_frame_completed_at,
            "last_analysis_completed_at": self.last_analysis_completed_at,
            "latest_frame_id": self.latest_frame_id,
            "latest_capture_dir": self.latest_capture_dir,
            "latest_report_path": self.latest_report_path,
            "latest_summary_path": self.latest_summary_path,
            "latest_index_path": self.latest_index_path,
            "latest_qpsk_mse": self.latest_qpsk_mse,
            "latest_qpsk_psnr": self.latest_qpsk_psnr,
            "latest_qpsk_header_valid": self.latest_qpsk_header_valid,
            "latest_qdpsk_mse": self.latest_qdpsk_mse,
            "latest_qdpsk_psnr": self.latest_qdpsk_psnr,
            "latest_qdpsk_header_valid": self.latest_qdpsk_header_valid,
            "latest_assets": dict(self.latest_assets),
            "latest_channel_stats": dict(self.latest_channel_stats),
            "first_header": self.first_header,
            "last_error": self.last_error,
            "progress": {
                str(channel_id): progress.to_dict()
                for channel_id, progress in sorted(self.progress.items())
            },
        }


class ReceiverService:
    """Run UDP receive and capture analysis on a background thread."""

    def __init__(
        self,
        listen_host: str = config.LISTEN_HOST,
        listen_port: int = config.LISTEN_PORT,
        auto_analyze: bool = True,
    ) -> None:
        self.listen_host = listen_host
        self.listen_port = int(listen_port)
        self.auto_analyze = auto_analyze
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = ReceiverServiceState(
            listen_host=self.listen_host,
            listen_port=self.listen_port,
        )

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._state.status = "starting"
            self._state.started_at = time.time()
            self._state.stopped_at = None
            self._state.last_error = None
            self._thread = threading.Thread(
                target=self._run,
                name="receiver-udp-service",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        thread = None
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            if thread is not None and thread.is_alive():
                self._state.status = "stopping"
        if thread is not None:
            thread.join(timeout=timeout)
        with self._lock:
            if self._thread is not None and not self._thread.is_alive():
                self._thread = None
            self._state.status = "stopped"
            self._state.stopped_at = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return self._state.to_dict()

    def analyze_latest_capture(self) -> CaptureAnalysisBundle:
        with self._lock:
            latest_capture_dir = self._state.latest_capture_dir
        if latest_capture_dir is None:
            raise FileNotFoundError("service has no completed capture yet")
        bundle = analyze_capture_directory(latest_capture_dir)
        self._store_analysis(bundle)
        return bundle

    def _run(self) -> None:
        with self._lock:
            self._state.status = "listening"
        try:
            run_receiver(
                listen_host=self.listen_host,
                listen_port=self.listen_port,
                save_completed_frames=True,
                on_progress=self._on_progress,
                on_idle=self._on_idle,
                on_first_datagram=self._on_first_datagram,
                on_first_header=self._on_first_header,
                on_frame_complete=self._on_frame_complete,
                stop_event=self._stop_event,
            )
            with self._lock:
                if self._state.status != "error":
                    self._state.status = "stopped"
                    self._state.stopped_at = time.time()
        except Exception:
            with self._lock:
                self._state.status = "error"
                self._state.last_error = traceback.format_exc()

    def _on_first_datagram(self, datagram: bytes, address: tuple[str, int]) -> None:
        del datagram, address
        with self._lock:
            self._state.last_packet_at = time.time()

    def _on_first_header(self, header: FragmentHeader) -> None:
        with self._lock:
            self._state.first_header = format_header(header)

    def _on_progress(self, channel_frame) -> None:
        percent = (channel_frame.received_count * 100.0) / channel_frame.chunk_count
        progress = ChannelProgressState(
            frame_id=channel_frame.frame_id,
            channel_id=channel_frame.channel_id,
            channel_name=channel_frame.channel_name,
            received_chunks=channel_frame.received_count,
            chunk_count=channel_frame.chunk_count,
            percent=percent,
            duplicate_chunks=channel_frame.duplicate_chunks,
        )
        with self._lock:
            self._state.status = "receiving"
            self._state.latest_frame_id = channel_frame.frame_id
            self._state.progress[channel_frame.channel_id] = progress

    def _on_idle(self, pending: list) -> None:
        with self._lock:
            if pending:
                self._state.status = "receiving"
            elif self._state.status not in ("analyzing", "error", "stopping"):
                self._state.status = "listening"

    def _on_frame_complete(
        self,
        frame_id: int,
        channels: dict[int, np.ndarray],
        outputs: dict[int, Path],
    ) -> None:
        capture_dir = _capture_dir_from_outputs(outputs)
        with self._lock:
            self._state.status = "complete"
            self._state.latest_frame_id = frame_id
            self._state.last_frame_completed_at = time.time()
            self._state.latest_capture_dir = str(capture_dir) if capture_dir else None
            self._state.progress = {
                channel_id: ChannelProgressState(
                    frame_id=frame_id,
                    channel_id=channel_id,
                    channel_name=CHANNEL_NAMES.get(channel_id, "UNKNOWN"),
                    received_chunks=config.EXPECTED_CHUNK_COUNT,
                    chunk_count=config.EXPECTED_CHUNK_COUNT,
                    percent=100.0,
                    duplicate_chunks=0,
                )
                for channel_id in channels
            }
        if self.auto_analyze and capture_dir is not None:
            with self._lock:
                self._state.status = "analyzing"
            try:
                bundle = analyze_capture_directory(capture_dir)
                self._store_analysis(bundle)
            except Exception:
                with self._lock:
                    self._state.status = "error"
                    self._state.last_error = traceback.format_exc()

    def _store_analysis(self, bundle: CaptureAnalysisBundle) -> None:
        with self._lock:
            self._state.status = "listening"
            self._state.last_analysis_completed_at = time.time()
            self._state.latest_capture_dir = str(bundle.capture_dir)
            self._state.latest_report_path = str(bundle.report_path)
            self._state.latest_summary_path = str(bundle.summary_path)
            self._state.latest_index_path = str(bundle.index_path)
            self._state.latest_qpsk_mse = bundle.qpsk_report.mse
            self._state.latest_qpsk_psnr = _psnr_text(bundle.qpsk_report.psnr)
            self._state.latest_qpsk_header_valid = bundle.qpsk_report.header_valid
            self._state.latest_qdpsk_mse = bundle.qdpsk_report.mse
            self._state.latest_qdpsk_psnr = _psnr_text(bundle.qdpsk_report.psnr)
            self._state.latest_qdpsk_header_valid = bundle.qdpsk_report.header_valid
            self._state.latest_assets = _analysis_assets(bundle)
            self._state.latest_channel_stats = {
                "qpsk": _channel_stats(bundle.qpsk_report),
                "qdpsk": _channel_stats(bundle.qdpsk_report),
            }
            self._state.last_error = None


def _capture_dir_from_outputs(outputs: dict[int, Path]) -> Path | None:
    if not outputs:
        return None
    first = next(iter(outputs.values()))
    return Path(first).parent


def _psnr_text(value: float) -> str:
    if value == float("inf"):
        return "inf"
    return "%.3f dB" % value


def _analysis_assets(bundle: CaptureAnalysisBundle) -> dict[str, str]:
    assets = {
        "capture_dir": str(bundle.capture_dir),
        "report": str(bundle.report_path),
        "summary": str(bundle.summary_path),
        "latest_report": str(bundle.latest_report_path),
        "index": str(bundle.index_path),
        "qpsk_recovered": str(bundle.qpsk_report.recovered_png),
        "qdpsk_recovered": str(bundle.qdpsk_report.recovered_png),
    }
    for plot in bundle.plots:
        key = plot.title.lower().replace(" ", "_")
        assets[key] = str(plot.image_path)
    return assets


def _channel_stats(channel) -> dict:
    return {
        "sample_count": channel.sample_count,
        "raw_average_power": channel.raw_average_power,
        "filtered_sample_count": channel.filtered_sample_count,
        "filtered_average_power": channel.filtered_average_power,
        "symbol_sample_count": channel.symbol_sample_count,
        "symbol_average_power": channel.symbol_average_power,
        "width": channel.width,
        "height": channel.height,
        "channels": channel.channels,
        "payload_bytes": channel.payload_bytes,
        "header_valid": channel.header_valid,
        "mse": channel.mse,
        "psnr": _psnr_text(channel.psnr),
    }
