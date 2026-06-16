"""Receiver command-line entry point."""

from __future__ import annotations

from receiver_service import ReceiverService
from web_app import WEB_HOST, WEB_PORT, run_http_server


def main() -> int:
    service = ReceiverService()
    service.start()
    try:
        run_http_server(service, WEB_HOST, WEB_PORT)
    except KeyboardInterrupt:
        print("\n[STOP] keyboard interrupt")
    finally:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
