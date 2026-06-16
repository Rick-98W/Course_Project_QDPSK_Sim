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
from receiver_service import ReceiverService


WEB_HOST = "127.0.0.1"
WEB_PORT = 9100


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
            self._send_file(config.REFERENCE_IMAGE_PATH)
            return
        if path.startswith("/static/"):
            self._send_static_file(config.BASE_DIR / "static", path[len("/static/") :])
            return
        if path.startswith("/captures/"):
            self._send_static_file(config.CAPTURE_DIR, path[len("/captures/") :])
            return
        if path.startswith("/reports/"):
            self._send_static_file(config.BASE_DIR / "reports", path[len("/reports/") :])
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
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        print("[HTTP] %s - %s" % (self.address_string(), format % args))

    def _send_template(self, name: str) -> None:
        self._send_file(config.BASE_DIR / "templates" / name)

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
        if target.suffix.lower() in (".html", ".css", ".js"):
            content_type += "; charset=utf-8"
        self._send_bytes(target.read_bytes(), content_type)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self._send_bytes(data, "application/json; charset=utf-8", status=status)

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
    server = ReceiverHttpServer((host, int(port)), service)
    print("Receiver HTTP API")
    print("listen: http://%s:%d" % (host, int(port)))
    server.serve_forever()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _state_with_urls(state: dict) -> dict:
    payload = dict(state)
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
    reports_root = (config.BASE_DIR / "reports").resolve()
    if _is_relative_to(path, capture_root):
        rel = path.relative_to(capture_root)
        return "/captures/" + _url_path(rel)
    if _is_relative_to(path, reports_root):
        rel = path.relative_to(reports_root)
        return "/reports/" + _url_path(rel)
    return None


def _url_path(path: Path) -> str:
    return str(path).replace(os.sep, "/")
