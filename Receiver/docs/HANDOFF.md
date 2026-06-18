# Receiver Handoff - 2026-06-16

Read this file first when resuming Receiver work with no prior chat context.

## Project Boundary

Repository root:

```text
C:\Users\Rick\PycharmProjects\QDPSK
```

Receiver root:

```text
C:\Users\Rick\PycharmProjects\QDPSK\Receiver
```

Ignore embedded/skill workflows unless the user explicitly asks. This is a Python RX/TX communication demo project.

Use exact interpreter:

```text
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe
```

Do not install dependencies automatically. If a package is missing, tell the user what to install.

## Current Status

Receiver is now a working PC-side HTML GUI receiver with pywebview shell.

It can:

- Start UDP listener automatically.
- Listen on `0.0.0.0:9000`.
- Serve local/LAN HTTP API on `0.0.0.0:9100`.
- Receive QPSK and QDPSK `complex64` UDP fragments from TX.
- Reassemble both channels by `(frame_id, channel_id)`.
- Save `.npy` captures.
- Analyze each completed capture automatically.
- Recover QPSK/QDPSK PNG images.
- Compare against TX-uploaded reference image.
- Show MSE, PSNR, header status, sample/power metrics.
- Generate RX-side Matplotlib analysis plots.
- Receive TX-side analysis plot package from TX.
- Display TX-side and RX-side plots in GUI.
- Export Markdown report with recovered images, RX plots, TX plots, and comparison tables.

The user has manually tested after directory restructuring and reported all tests passed.

## Current Directory Structure

Important source layout:

```text
Receiver/
  main.py
  desktop_app.py
  config.py
  README.md
  docs/
    HANDOFF.md
    OVERALL_PLAN.md
    DEMO_RUNBOOK.md
    DEVELOPMENT_LOG.md
    DEVELOPMENT_PLAN.md
  core/
    capture.py
    frame_buffer.py
    network_info.py
    packet.py
    receiver_service.py
    udp_receiver.py
  analysis/
    analysis.py
    demodulation.py
    dsp.py
    export_markdown.py
    image_output.py
    image_recovery.py
    plotter.py
    reference_image.py
    report.py
  storage/
    reference_store.py
    tx_plot_store.py
  web/
    web_app.py
    templates/index.html
    static/app.js
    static/style.css
  tools/
    analyze_latest_capture.py
    offline_reassembly_check.py
  runtime/
    captures/
    reports/
    reference/
    exports/
    tx_plots/
  scratch/
```

Package directories contain `__init__.py`.

Runtime outputs are under `Receiver/runtime/` and are git-ignored.

## Import Rules

Use package imports, not old flat imports.

Examples:

```python
from core.receiver_service import ReceiverService
from web.web_app import create_http_server
from analysis.analysis import analyze_capture_directory
from storage.reference_store import reference_available
from storage.tx_plot_store import save_tx_plot_zip
```

Do not reintroduce old imports such as:

```python
from receiver_service import ReceiverService
from analysis import analyze_latest_capture
from packet import CHANNEL_QPSK
```

## Runtime Paths

Defined in `Receiver/config.py`:

```text
RUNTIME_DIR = Receiver/runtime
CAPTURE_DIR = Receiver/runtime/captures
REPORT_DIR = Receiver/runtime/reports
REFERENCE_DIR = Receiver/runtime/reference
EXPORT_DIR = Receiver/runtime/exports
TX_PLOT_DIR = Receiver/runtime/tx_plots
```

HTTP-served paths:

```text
/captures/...  -> Receiver/runtime/captures/...
/reports/...   -> Receiver/runtime/reports/...
/tx-plots/...  -> Receiver/runtime/tx_plots/...
/static/...    -> Receiver/web/static/...
/reference-image -> Receiver/runtime/reference/tx_reference.png
```

## Run

Desktop GUI:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe desktop_app.py
```

Browser debug mode:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe main.py
```

Open:

```text
http://127.0.0.1:9100
```

Raw state:

```text
http://127.0.0.1:9100/api/state
```

If GUI state looks stale, check for duplicate old Python processes on ports `9000`, `9100`, or `8000`.

## TX/RX LAN Model

The final intended demo is:

```text
Windows PC = Receiver
Orange Pi = Transmitter
phone hotspot = offline LAN only
```

No internet service is involved. HTTP is only local/LAN communication between TX and RX.

RX exposes:

```text
UDP 9000: IQ fragments
TCP 9100: GUI/API/reference image/TX plot upload
```

TX sends to `target_host:target_port`, normally:

```text
192.168.x.x:9000
```

TX also uploads to:

```text
http://<target_host>:<target_port + 100>/api/reference-image
http://<target_host>:<target_port + 100>/api/tx-plots
```

## Protocol

UDP payload is not raw image bytes and not a bitstream. It is sampled digital baseband IQ after RRC shaping and channel impairment.

Each UDP datagram:

```text
26-byte application header + complex64 payload
```

Header struct:

```python
struct.Struct(">2sBBIBBHHIII")
```

Channel IDs:

```text
0 = QPSK
1 = QDPSK
```

Current expected frame:

```text
samples per channel: 393568
chunks per channel: 2249
total packets: 4498
```

## Reference Image And TX Plot Uploads

RX no longer reads the original image from the TX directory.

TX uploads the fixed source image to:

```text
POST /api/reference-image
```

RX saves it as:

```text
Receiver/runtime/reference/tx_reference.png
```

TX also uploads a zip containing 10 transmitter-side plot PNGs to:

```text
POST /api/tx-plots
```

RX saves latest TX plots under:

```text
Receiver/runtime/tx_plots/
```

After a capture analysis completes, RX copies those TX plots into:

```text
Receiver/runtime/captures/frame_*/tx_plots/
```

## GUI State

RX GUI displays:

- UDP status and instance ID.
- TX target hint and LAN IP addresses.
- Reference image status.
- QPSK/QDPSK fragment progress.
- Original reference image.
- QPSK/QDPSK recovered images.
- QPSK/QDPSK MSE, PSNR, header fallback status.
- RX-side plots:
  - QPSK 接收星座图
  - QDPSK 接收星座图
  - QDPSK 差分星座图
  - QPSK 接收眼图
  - QDPSK 接收眼图
  - 接收波形幅度
  - 接收相位轨迹
  - 接收功率谱
  - 误差矢量幅度
- TX-side plots at bottom as two columns:
  - QPSK left
  - QDPSK right
  - five rows by plot type

## Markdown Export

Button:

```text
导出 Markdown
```

Generates:

```text
Receiver/runtime/captures/frame_*/analysis_export.md
Receiver/runtime/exports/latest_analysis_export.md
Receiver/runtime/exports/latest_analysis_assets/*.png
```

Export includes:

- QPSK recovered PNG.
- QDPSK recovered PNG.
- RX-side analysis plots.
- TX-side analysis plots.
- QPSK/QDPSK metric comparison table.

Export intentionally excludes the original reference image.

## Current Demo Boundary

Current source image is fixed on TX:

```text
Transmitter/raw_pic_64.png
64x64 RGB
```

Receiver fallback recovery assumes fixed `64x64x3` RGB when `IMG0` header is damaged.

Arbitrary image size support is deferred because it requires coordinated TX/RX changes.

## Validation Commands

Run after import/path work:

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

Last verified state:

```text
RX compileall: pass
RX JS check: pass
offline_reassembly_check: pass
analyze_latest_capture: pass
HTTP server construction smoke: pass
Manual user test after path reorganization: pass
```

## Current Plan

Immediate next step:

```text
Prepare Orange Pi TX migration and real LAN testing.
```

Recommended next rounds:

1. Run PC-local sanity after any import/path changes.
2. Move/copy `Transmitter/` to Orange Pi.
3. Install/verify TX Python dependencies on Orange Pi.
4. Connect PC and Orange Pi to same phone hotspot.
5. Start RX desktop app on PC.
6. Set TX target to RX dashboard `TX 目标地址`.
7. Send multiple frames with phase/SNR demo values.
8. Verify RX GUI updates without manual refresh.
9. Verify TX plots and Markdown export include all expected images.
10. Only after LAN behavior is stable, prepare packaging notes and PyInstaller work.

Deferred:

- Arbitrary image dimensions.
- Timing recovery.
- Carrier recovery.
- BER estimation.
- int16 IQ compression.
- EXE packaging.
