"""Local HTTP API for the Receiver GUI."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import config
from core.receiver_service import ReceiverService
from storage.reference_store import reference_available, save_reference_png
from storage.tx_plot_store import save_tx_plot_zip


WEB_HOST = "0.0.0.0"
WEB_PORT = 9100
SERVER_VERSION = "rx-reference-state-2026-06-16"


class ReceiverHttpServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        service: ReceiverService,
    ) -> None:
        super().__init__(server_address, ReceiverRequestHandler)
        self.service = service


class ReceiverRequestHandler(BaseHTTPRequestHandler):
    server: ReceiverHttpServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_template("index.html")
            return
        if path == "/api/state":
            self._send_json(_state_with_urls(self.server.service.snapshot()))
            return
        if path == "/reference-image":
            if not reference_available():
                self._send_json(
                    {"error": "reference image not uploaded"},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            self._send_file(config.REFERENCE_IMAGE_PATH)
            return
        if path.startswith("/static/"):
            self._send_static_file(config.BASE_DIR / "web" / "static", path[len("/static/") :])
            return
        if path.startswith("/captures/"):
            self._send_static_file(config.CAPTURE_DIR, path[len("/captures/") :])
            return
        if path.startswith("/reports/"):
            self._send_static_file(config.REPORT_DIR, path[len("/reports/") :])
            return
        if path.startswith("/exports/"):
            self._send_static_file(config.EXPORT_DIR, path[len("/exports/") :])
            return
        if path.startswith("/tx-plots/"):
            self._send_static_file(config.TX_PLOT_DIR, path[len("/tx-plots/") :])
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/start":
            self.server.service.start()
            self._send_json(_state_with_urls(self.server.service.snapshot()))
            return
        if path == "/api/stop":
            self.server.service.stop()
            self._send_json(_state_with_urls(self.server.service.snapshot()))
            return
        if path == "/api/analyze-latest":
            try:
                self.server.service.analyze_latest_capture()
            except Exception as exc:
                self._send_json(
                    {
                        "error": str(exc),
                        "state": _state_with_urls(self.server.service.snapshot()),
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            self._send_json(_state_with_urls(self.server.service.snapshot()))
            return
        if path == "/api/settings":
            try:
                payload = self._read_json(4096)
                self.server.service.update_incomplete_frame_settings(
                    timeout_sec=payload.get("incomplete_frame_analysis_timeout_sec"),
                    min_completion_ratio=payload.get("incomplete_frame_min_completion_ratio"),
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(_state_with_urls(self.server.service.snapshot()))
            return
        if path == "/api/export-latest":
            try:
                export_path = self.server.service.export_latest_capture()
            except Exception as exc:
                self._send_json(
                    {
                        "error": str(exc),
                        "state": _state_with_urls(self.server.service.snapshot()),
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            payload = _state_with_urls(self.server.service.snapshot())
            payload["export_path"] = str(export_path)
            payload["export_url"] = _path_to_url(export_path)
            self._send_json(payload)
            return
        if path == "/api/reference-image":
            try:
                data = self._read_body(int(config.MAX_REFERENCE_IMAGE_BYTES))
                reference = save_reference_png(data)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    "ok": True,
                    "reference_path": str(config.REFERENCE_IMAGE_PATH),
                    "width": reference.width,
                    "height": reference.height,
                    "channels": reference.channels,
                }
            )
            return
        if path == "/api/tx-plots":
            try:
                data = self._read_body(int(config.MAX_TX_PLOTS_BYTES))
                assets = save_tx_plot_zip(data)
                self.server.service.note_tx_plots_received()
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    "ok": True,
                    "plot_count": len(assets),
                    "state": _state_with_urls(self.server.service.snapshot()),
                }
            )
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        print("[HTTP] %s - %s" % (self.address_string(), format % args))

    def _send_template(self, name: str) -> None:
        self._send_file(config.BASE_DIR / "web" / "templates" / name)

    def _send_static_file(self, root: Path, relative_url_path: str) -> None:
        root = Path(root).resolve()
        relative = unquote(relative_url_path).replace("/", "\\")
        target = (root / relative).resolve()
        if not _is_relative_to(target, root) or not target.is_file():
            self._send_json({"error": "file not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_file(target)

    def _send_file(self, path: str | Path) -> None:
        target = Path(path)
        if not target.is_file():
            self._send_json({"error": "file not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix.lower() == ".md":
            content_type = "text/markdown"
        if target.suffix.lower() in (".html", ".css", ".js"):
            content_type += "; charset=utf-8"
        elif target.suffix.lower() == ".md":
            content_type += "; charset=utf-8"
        self._send_bytes(target.read_bytes(), content_type)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self._send_bytes(data, "application/json; charset=utf-8", status=status)

    def _read_body(self, max_bytes: int) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("request body is empty")
        if length > int(max_bytes):
            raise ValueError("request body is too large")
        return self.rfile.read(length)

    def _read_json(self, max_bytes: int) -> dict:
        data = self._read_body(max_bytes)
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _send_bytes(
        self,
        data: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def run_http_server(
    service: ReceiverService,
    host: str = WEB_HOST,
    port: int = WEB_PORT,
) -> None:
    server = create_http_server(service, host, port)
    print("Receiver HTTP API")
    print("listen: http://%s:%d" % (host, int(port)))
    server.serve_forever()


def create_http_server(
    service: ReceiverService,
    host: str = WEB_HOST,
    port: int = WEB_PORT,
) -> ReceiverHttpServer:
    return ReceiverHttpServer((host, int(port)), service)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _state_with_urls(state: dict) -> dict:
    payload = dict(state)
    payload["server_version"] = SERVER_VERSION
    payload["reference_available"] = reference_available()
    payload["reference_path"] = str(config.REFERENCE_IMAGE_PATH)
    payload["latest_asset_urls"] = {
        key: _path_to_url(value)
        for key, value in state.get("latest_assets", {}).items()
        if _path_to_url(value)
    }
    return payload


def _path_to_url(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value).resolve()
    capture_root = config.CAPTURE_DIR.resolve()
    reports_root = config.REPORT_DIR.resolve()
    exports_root = config.EXPORT_DIR.resolve()
    tx_plots_root = config.TX_PLOT_DIR.resolve()
    if _is_relative_to(path, capture_root):
        rel = path.relative_to(capture_root)
        return "/captures/" + _url_path(rel)
    if _is_relative_to(path, reports_root):
        rel = path.relative_to(reports_root)
        return "/reports/" + _url_path(rel)
    if _is_relative_to(path, exports_root):
        rel = path.relative_to(exports_root)
        return "/exports/" + _url_path(rel)
    if _is_relative_to(path, tx_plots_root):
        rel = path.relative_to(tx_plots_root)
        return "/tx-plots/" + _url_path(rel)
    return None


def _url_path(path: Path) -> str:
    return str(path).replace(os.sep, "/")
