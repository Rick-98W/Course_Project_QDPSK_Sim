# Receiver Execution Plan

This is the current source of truth for Receiver work.

Read first:

```text
Receiver/docs/HANDOFF.md
```

## Current Product Target

```text
Windows PC Receiver app
 -> opens HTML GUI through pywebview
 -> starts UDP listening automatically
 -> receives QPSK/QDPSK IQ frames from TX
 -> receives TX reference image and TX analysis plots
 -> analyzes completed frames automatically
 -> updates images, plots, metrics, and status repeatedly
 -> exports Markdown evidence package
```

## Current Implemented State

Completed:

- Organized package layout:
  - `core/`
  - `analysis/`
  - `storage/`
  - `web/`
  - `docs/`
  - `runtime/`
- UDP listener on `0.0.0.0:9000`.
- HTTP GUI/API on `0.0.0.0:9100`.
- pywebview desktop shell at `desktop_app.py`.
- LAN target hint in GUI.
- TX reference image upload at `POST /api/reference-image`.
- TX plot package upload at `POST /api/tx-plots`.
- Fragment reassembly for both channels.
- Automatic capture saving and analysis.
- Recovered image display.
- RX-side plot display.
- TX-side plot display in two columns, QPSK left and QDPSK right.
- Markdown export with recovered images, RX plots, TX plots, and metrics.
- Runtime outputs under `Receiver/runtime/`.

## Immediate Next Step

Prepare and run Orange Pi LAN testing over the phone-hotspot network.

Real-device checklist:

1. Connect Windows PC and Orange Pi to the same phone hotspot.
2. Start Receiver desktop app on the PC:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe desktop_app.py
```

3. Read `TX 目标地址` in the Receiver dashboard.
4. Run Transmitter web app on Orange Pi.
5. Set TX target to the displayed PC LAN address, normally `192.168.x.x:9000`.
6. Click TX `发送 UDP`.
7. Confirm Receiver GUI updates without manual refresh.
8. Confirm RX receives:
   - UDP IQ
   - reference PNG
   - 10 TX-side plot PNGs
9. Confirm `导出 Markdown` includes:
   - QPSK/QDPSK recovered images
   - 9 RX-side plots
   - 10 TX-side plots
   - metric comparison table
10. If packets or uploads fail, check Windows Firewall inbound UDP `9000` and TCP `9100`.

## Validation Commands

Use these after changes:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m compileall -q .
node --check web\static\app.js
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\offline_reassembly_check.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Smoke check:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -c "from core.receiver_service import ReceiverService; from web.web_app import create_http_server, _state_with_urls; s=ReceiverService(); p=_state_with_urls(s.snapshot()); server=create_http_server(s, '127.0.0.1', 0); print(p['server_version']); print(p['reference_path']); print(server.server_address); server.server_close()"
```

## Stop Criteria For Course Demo

Receiver can be considered ready when:

1. PC Receiver GUI starts with one command.
2. UDP listener starts automatically.
3. TX can send repeatedly and RX GUI updates each time.
4. RX GUI shows reference, QPSK recovered, QDPSK recovered, RX plots, TX plots, metrics, and status.
5. Markdown export works and images load.
6. PC-local test passes.
7. Orange Pi TX to PC RX LAN test passes.

## Deferred Work

Do not do these before LAN testing is stable:

- PyInstaller packaging.
- Arbitrary image dimensions.
- Gardner timing recovery.
- Carrier recovery.
- Group synchronization.
- `int16` IQ transport.
- BER estimation.
- PDF/docx export.
