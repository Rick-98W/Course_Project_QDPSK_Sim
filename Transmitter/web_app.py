"""Standard-library HTTP app for the transmitter control page."""

from __future__ import annotations

import json
import mimetypes
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import config
from tx_pipeline import print_pipeline_summary, run_transmitter_pipeline


TEMPLATE_DIR = config.BASE_DIR / "templates"
STATIC_DIR = config.BASE_DIR / "static"


class TransmitterState:
    def __init__(self):
        self.snr_db = float(config.SNR_DB)
        self.phase_deg = float(config.PHASE_DEG)
        self.target_host = str(config.TARGET_HOST)
        self.target_port = int(config.TARGET_PORT)
        self.last_result = run_transmitter_pipeline(
            snr_db=self.snr_db,
            phase_deg=self.phase_deg,
            target_host=self.target_host,
            target_port=self.target_port,
            send_udp=False,
        )

    def update_config(self, payload):
        if "snr_db" in payload:
            self.snr_db = clamp_float(payload["snr_db"], config.SNR_MIN_DB, config.SNR_MAX_DB)
        if "phase_deg" in payload:
            self.phase_deg = clamp_float(
                payload["phase_deg"], config.PHASE_MIN_DEG, config.PHASE_MAX_DEG
            )
        if "target_host" in payload:
            self.target_host = normalize_host(payload["target_host"])
        if "target_port" in payload:
            self.target_port = normalize_port(payload["target_port"])
        print(
            "[CONFIG] snr_db=%.3f phase_deg=%.3f target=%s:%d"
            % (
                self.snr_db,
                self.phase_deg,
                self.target_host,
                self.target_port,
            ),
            flush=True,
        )
        return self.as_json()

    def render(self):
        print(
            "[RENDER] start snr_db=%.3f phase_deg=%.3f"
            % (self.snr_db, self.phase_deg),
            flush=True,
        )
        self.last_result = run_transmitter_pipeline(
            snr_db=self.snr_db,
            phase_deg=self.phase_deg,
            target_host=self.target_host,
            target_port=self.target_port,
            send_udp=False,
        )
        print_action_summary("RENDER", self.last_result)
        return self.as_json()

    def send(self):
        print(
            "[SEND] start snr_db=%.3f phase_deg=%.3f target=%s:%d"
            % (
                self.snr_db,
                self.phase_deg,
                self.target_host,
                self.target_port,
            ),
            flush=True,
        )
        self.last_result = run_transmitter_pipeline(
            snr_db=self.snr_db,
            phase_deg=self.phase_deg,
            target_host=self.target_host,
            target_port=self.target_port,
            send_udp=True,
        )
        print_action_summary("SEND", self.last_result)
        return self.as_json()

    def as_json(self):
        return {
            "config": {
                "snr_db": self.snr_db,
                "phase_deg": self.phase_deg,
                "target_host": self.target_host,
                "target_port": self.target_port,
                "web_host": config.WEB_HOST,
                "web_port": config.WEB_PORT,
            },
            "result": self.last_result,
            "plots": plot_urls(),
            "source_image_url": "/source-image",
        }


def create_handler(state):
    class TransmitterHandler(BaseHTTPRequestHandler):
        server_version = "TransmitterHTTP/1.0"

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/":
                self._send_file(TEMPLATE_DIR / "index.html", "text/html; charset=utf-8")
            elif path == "/source-image":
                self._send_file(config.IMAGE_PATH, "image/png")
            elif path == "/api/state":
                self._send_json(state.as_json())
            elif path == "/api/tx-plots":
                self._send_json(plot_urls())
            elif path.startswith("/static/"):
                self._send_static(path)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "not found")

        def do_POST(self):
            parsed = urlparse(self.path)
            payload = self._read_json_body()
            try:
                if parsed.path == "/api/config":
                    self._send_json(state.update_config(payload))
                elif parsed.path == "/api/render":
                    self._send_json(state.render())
                elif parsed.path == "/api/send":
                    self._send_json(state.send())
                else:
                    self.send_error(HTTPStatus.NOT_FOUND, "not found")
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        def log_message(self, format, *args):
            print("%s - %s" % (self.address_string(), format % args))

        def _read_json_body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def _send_json(self, payload, status=HTTPStatus.OK):
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self, request_path):
            relative = unquote(request_path.removeprefix("/static/"))
            target = (STATIC_DIR / relative).resolve()
            static_root = STATIC_DIR.resolve()
            if static_root not in target.parents and target != static_root:
                self.send_error(HTTPStatus.FORBIDDEN, "invalid static path")
                return
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self._send_file(target, content_type)

        def _send_file(self, path, content_type):
            target = Path(path)
            if not target.exists() or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "file not found")
                return
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return TransmitterHandler


def plot_urls():
    return {
        "qpsk": {
            "psd": versioned_static_url("generated/qpsk_psd.png"),
            "eye": versioned_static_url("generated/qpsk_eye.png"),
            "constellation": versioned_static_url("generated/qpsk_constellation.png"),
            "impaired_constellation": versioned_static_url(
                "generated/qpsk_impaired_constellation.png"
            ),
            "impaired_eye": versioned_static_url("generated/qpsk_impaired_eye.png"),
        },
        "qdpsk": {
            "psd": versioned_static_url("generated/qdpsk_psd.png"),
            "eye": versioned_static_url("generated/qdpsk_eye.png"),
            "constellation": versioned_static_url("generated/qdpsk_constellation.png"),
            "impaired_constellation": versioned_static_url(
                "generated/qdpsk_impaired_constellation.png"
            ),
            "impaired_eye": versioned_static_url("generated/qdpsk_impaired_eye.png"),
        },
    }


def versioned_static_url(relative_path):
    target = STATIC_DIR / relative_path
    version = target.stat().st_mtime_ns if target.exists() else time.time_ns()
    return "/static/%s?v=%d" % (relative_path.replace("\\", "/"), version)


def normalize_host(value):
    host = str(value).strip()
    if not host:
        raise ValueError("target_host cannot be empty")
    return host


def normalize_port(value):
    port = int(value)
    if port < 1 or port > 65535:
        raise ValueError("target_port must be in 1..65535")
    return port


def clamp_float(value, minimum, maximum):
    number = float(value)
    if number < float(minimum):
        return float(minimum)
    if number > float(maximum):
        return float(maximum)
    return number


def print_action_summary(action, result):
    udp = result["udp"]
    channel = result["channel"]
    send_result = udp["send_result"]
    print(
        "[%s] generated_at=%s qpsk_packets=%d qdpsk_packets=%d sent=%s"
        % (
            action,
            result["generated_at"],
            udp["qpsk_packet_count"],
            udp["qdpsk_packet_count"],
            send_result["sent"],
        ),
        flush=True,
    )
    print(
        "[%s] qpsk_snr=%.3f qdpsk_snr=%.3f qpsk_power=%.6f qdpsk_power=%.6f"
        % (
            action,
            channel["qpsk_estimated_snr_db"],
            channel["qdpsk_estimated_snr_db"],
            channel["qpsk_impaired_power"],
            channel["qdpsk_impaired_power"],
        ),
        flush=True,
    )
    print(
        "[%s] udp_packets_sent=%d udp_total_bytes=%d udp_elapsed_sec=%.3f"
        % (
            action,
            send_result["packet_count"],
            send_result["total_bytes"],
            send_result["elapsed_sec"],
        ),
        flush=True,
    )
    print(
        "[%s] qpsk_plots psd=%s eye=%s constellation=%s"
        % (
            action,
            result["plots"]["qpsk"]["psd"],
            result["plots"]["qpsk"]["eye"],
            result["plots"]["qpsk"]["constellation"],
        ),
        flush=True,
    )
    print(
        "[%s] qpsk_impaired_constellation=%s"
        % (
            action,
            result["plots"]["qpsk"]["impaired_constellation"],
        ),
        flush=True,
    )
    print(
        "[%s] qpsk_impaired_eye=%s"
        % (
            action,
            result["plots"]["qpsk"]["impaired_eye"],
        ),
        flush=True,
    )
    print(
        "[%s] qdpsk_plots psd=%s eye=%s constellation=%s"
        % (
            action,
            result["plots"]["qdpsk"]["psd"],
            result["plots"]["qdpsk"]["eye"],
            result["plots"]["qdpsk"]["constellation"],
        ),
        flush=True,
    )
    print(
        "[%s] qdpsk_impaired_constellation=%s"
        % (
            action,
            result["plots"]["qdpsk"]["impaired_constellation"],
        ),
        flush=True,
    )
    print(
        "[%s] qdpsk_impaired_eye=%s"
        % (
            action,
            result["plots"]["qdpsk"]["impaired_eye"],
        ),
        flush=True,
    )


def run_web_app():
    state = TransmitterState()
    print_pipeline_summary(state.last_result)
    server = ThreadingHTTPServer(
        (config.WEB_HOST, int(config.WEB_PORT)),
        create_handler(state),
    )
    print("web server URL: http://127.0.0.1:%d" % int(config.WEB_PORT))
    print("browser open status: manual")
    server.serve_forever()
