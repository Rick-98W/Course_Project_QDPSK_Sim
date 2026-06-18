"""pywebview desktop entry point for the Receiver dashboard."""

from __future__ import annotations

import threading

import webview

from core.receiver_service import ReceiverService
from web.web_app import WEB_HOST, WEB_PORT, create_http_server


WINDOW_TITLE = "QDPSK Receiver"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 820


class ReceiverDesktopApp:
    def __init__(self) -> None:
        self.service = ReceiverService()
        self.http_server = create_http_server(self.service, WEB_HOST, WEB_PORT)
        self.http_thread = threading.Thread(
            target=self.http_server.serve_forever,
            name="receiver-http-server",
            daemon=True,
        )

    @property
    def url(self) -> str:
        return "http://127.0.0.1:%d" % int(WEB_PORT)

    def start_backend(self) -> None:
        self.service.start()
        self.http_thread.start()
        print("Receiver desktop backend")
        print("listen: %s" % self.url)

    def stop_backend(self) -> None:
        self.http_server.shutdown()
        self.http_server.server_close()
        self.service.stop()


def main() -> int:
    app = ReceiverDesktopApp()
    app.start_backend()
    try:
        window = webview.create_window(
            WINDOW_TITLE,
            app.url,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
        )
        webview.start()
        del window
    finally:
        app.stop_backend()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
