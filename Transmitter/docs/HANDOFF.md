# Transmitter Handoff - 2026-06-16

Read this file first when resuming Transmitter work with no prior chat context.

## Project Boundary

Repository root:

```text
C:\Users\Rick\PycharmProjects\QDPSK
```

Transmitter root:

```text
C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
```

Use exact interpreter:

```text
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe
```

Do not install packages automatically. If a dependency is missing, tell the user what to install.

## Project Role

TX is the Orange Pi side for the final LAN demo.

It simulates the full digital communication transmit chain:

```text
raw_pic_64.png
 -> IMG0 image frame
 -> bitstream
 -> QPSK and QDPSK symbols
 -> RRC pulse shaping
 -> simulated channel impairment: AWGN + fixed phase rotation
 -> sampled complex64 baseband IQ
 -> UDP fragmented send to RX
```

Important:

- UDP sends sampled `complex64` IQ.
- UDP does not send raw image bytes.
- UDP does not send the bitstream directly.
- Phone hotspot is only LAN transport.
- AWGN/phase rotation are simulated inside TX Python code.

## Current Directory Structure

```text
Transmitter/
  main.py
  config.py
  raw_pic_64.png
  README.md
  docs/
    HANDOFF.md
    ORANGE_PI_MIGRATION.md
    DEMO_LIMITS.md
    DEVELOPMENT_LOG.md
    DEVELOPMENT_PLAN.md
  core/
    bitstream.py
    channel.py
    image_source.py
    modulation.py
    packet.py
    preview_dump.py
    tx_pipeline.py
    udp_sender.py
  analysis/
    analysis.py
    plotter.py
    plotter_fallback.py
  web/
    web_app.py
    templates/index.html
    static/app.js
    static/style.css
    static/generated/
```

Package directories contain `__init__.py`.

Generated TX plots live under:

```text
Transmitter/web/static/generated/
```

## Import Rules

Use package imports after directory reorganization.

Examples:

```python
from web.web_app import run_web_app
from core.tx_pipeline import run_transmitter_pipeline
from analysis.analysis import compute_psd
from analysis.plotter import render_all_tx_plots
from core.packet import fragment_iq_stream
```

Do not reintroduce old flat imports such as:

```python
from tx_pipeline import run_transmitter_pipeline
from packet import fragment_iq_stream
from plotter import render_all_tx_plots
```

## Run

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe main.py
```

Open:

```text
http://127.0.0.1:8000
```

Do not open `web/templates/index.html` directly. It needs the Python HTTP API.

If Chrome shows stale behavior, stop duplicate Python processes on ports `8000` and `9100`, restart TX/RX, then hard refresh.

## Orange Pi Migration

Detailed copy/run notes for the Orange Pi side are recorded in:

```text
Transmitter/docs/ORANGE_PI_MIGRATION.md
```

Short version:

- Copy the whole `Transmitter/` folder to Orange Pi.
- Do not copy the Windows conda environment.
- Create a fresh Linux/ARM conda environment on Orange Pi.
- Install at least `numpy` and `matplotlib`.
- Verify/install `SimHei` and `Times New Roman` fonts.
- Run from the copied `Transmitter/` directory with `python main.py`.
- Open `http://127.0.0.1:8000` in Orange Pi Chromium.
- In TX page, target the PC Receiver LAN IP and UDP port `9000`.
- PC Receiver must allow inbound UDP `9000` and TCP `9100`.

## Current User Workflow

1. Start RX first.
2. Start TX.
3. Open TX page.
4. Set target host/port:
   - PC local: `127.0.0.1:9000`
   - LAN: RX dashboard `TX 目标地址`, normally `192.168.x.x:9000`
5. Set SNR/phase.
6. Click `发送 UDP`.

On send, TX:

- Uploads fixed source image to RX:

```text
POST http://<target_host>:<target_port + 100>/api/reference-image
```

- Renders channel-post plots.
- Sends QPSK/QDPSK UDP IQ fragments.
- Packages 10 TX analysis PNGs and uploads to RX:

```text
POST http://<target_host>:<target_port + 100>/api/tx-plots
```

## Fixed Demo Image

Current source:

```text
Transmitter/raw_pic_64.png
64x64 RGB
```

TX validates fixed dimensions. Arbitrary image dimensions are deferred because RX fallback recovery assumes `64x64x3`.

## Current Controls

```text
SNR range: -3.0 .. 30.0 dB
Phase range: -90 .. +90 deg
Target host/port editable at runtime
```

Good demo cases:

```text
30 dB, 0 deg     -> QPSK/QDPSK both good
30 dB, 75 deg    -> QPSK fails by quadrant/phase ambiguity, QDPSK survives
6 dB, 0 deg      -> noise visible, QDPSK can show differential loss
6 dB, 90 deg     -> QPSK dominated by phase ambiguity, QDPSK remains robust
-3 dB cases      -> very harsh noise demo
```

## Generated TX Plots

TX page shows 10 images:

```text
QPSK 信道后星座图      qpsk_impaired_constellation.png
QDPSK 信道后星座图     qdpsk_impaired_constellation.png
QPSK 信道后眼图        qpsk_impaired_eye.png
QDPSK 信道后眼图       qdpsk_impaired_eye.png
QPSK 信道前基带功率谱  qpsk_psd.png
QDPSK 信道前基带功率谱 qdpsk_psd.png
QPSK 信道前基带眼图    qpsk_eye.png
QDPSK 信道前基带眼图   qdpsk_eye.png
QPSK 信道前星座图      qpsk_constellation.png
QDPSK 信道前星座图     qdpsk_constellation.png
```

TX uploads the same 10 PNGs to RX after `Send UDP`.

RX GUI displays these TX plots at the bottom as:

```text
QPSK column | QDPSK column
5 rows by plot type
```

## Protocol

UDP packet format:

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

## Font Policy

HTML GUI and Matplotlib plots should preserve:

```text
Chinese: SimHei
English/numbers: Times New Roman
```

Matplotlib mixed Chinese/English labels are handled by splitting text runs. Do not regress to a single Chinese-first font family for all plot text.

## Validation Commands

Run after import/path changes:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe -m compileall -q .
node --check web\static\app.js
```

Smoke check:

```powershell
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe -c "from web.web_app import TransmitterState; s=TransmitterState().as_json(); print(s['image_loaded']); print(s['result']['image']['path']); print(s['plots']['qpsk']['psd'])"
```

Last verified state:

```text
TX compileall: pass
TX JS check: pass
TransmitterState smoke: pass
Manual user test after path reorganization: pass
```

## Current Plan

Immediate next step:

```text
Prepare Orange Pi migration and real LAN testing with PC Receiver.
```

Recommended next rounds:

1. Copy/move `Transmitter/` to Orange Pi.
2. Verify Python, NumPy, Matplotlib, and fonts on Orange Pi.
3. Start PC Receiver.
4. Connect PC and Orange Pi to phone hotspot.
5. Open TX page in Orange Pi Chromium.
6. Set target to RX dashboard `TX 目标地址`.
7. Send demo frames for key SNR/phase cases.
8. Confirm RX receives IQ, reference image, and TX plot zip.
9. Confirm RX Markdown export includes recovered images, RX plots, and TX plots.
10. Only after LAN behavior is stable, consider packaging/final report polish.

Deferred:

- Arbitrary image dimensions.
- int16 IQ transport.
- Automatic repeated-send mode.
- More advanced sync/channel recovery.
- Packaging.
