# Receiver Handoff - 2026-06-15

This file is the first document to read when resuming Receiver work without prior chat context.

Current planning entry point:

```text
Receiver/OVERALL_PLAN.md
```

## Project Boundary

Repository root:

```text
C:\Users\Rick\PycharmProjects\QDPSK
```

Receiver project root:

```text
C:\Users\Rick\PycharmProjects\QDPSK\Receiver
```

This is a Python project. Ignore Trellis/skill workflows for this project unless the user explicitly asks otherwise.

Keep Receiver code isolated under `Receiver\` unless the user explicitly allows editing both sides. The user has previously allowed two-sided edits only for demo range limits and matching documentation.

## Interpreter And Dependencies

Receiver interpreter:

```text
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe
```

Transmitter interpreter:

```text
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe
```

Dependency rule:

- Do not install packages automatically.
- If a dependency is missing, stop and tell the user what to install in conda.
- Receiver currently uses NumPy and standard-library modules.
- Transmitter currently uses NumPy and Matplotlib.
- Planned GUI/runtime dependencies are `pywebview`, `matplotlib`, and later `pyinstaller`.
- Do not assume `pywebview` is present until the user verifies it in the environment.

## Current End-To-End State

Final Receiver target:

```text
Windows PC app / later EXE
 -> opens an HTML-based GUI
 -> starts UDP listening automatically
 -> receives TX frames repeatedly
 -> reassembles and analyzes each new frame automatically
 -> refreshes images, plots, metrics, and receive status in the GUI
```

Current implementation is the reusable analysis base for that GUI target, not the final GUI yet.

Current PC-local TX/RX path works through image recovery:

```text
Transmitter raw_pic_64.png
 -> IMG0 image frame
 -> bitstream
 -> QPSK and QDPSK modulation
 -> RRC pulse shaping
 -> AWGN + phase rotation
 -> complex64 UDP fragments
 -> Receiver reassembly
 -> .npy capture files
 -> offline matched filtering and demodulation
 -> recovered PNG files
 -> MSE / PSNR comparison
```

Receiver can:

- Listen on UDP `127.0.0.1:9000`.
- Parse the current 26-byte fragmented UDP header.
- Buffer fragments by `(frame_id, channel_id)`.
- Reassemble QPSK and QDPSK `complex64` IQ arrays.
- Save complete captures under `Receiver\captures\frame_*\`.
- Analyze the latest capture offline.
- Recover `qpsk_recovered.png` and `qdpsk_recovered.png`.
- Compare recovered images against `Transmitter\raw_pic_64.png`.
- Produce degraded PNG output even if the image header is damaged.
- Produce a static latest-capture HTML report with original / QPSK / QDPSK image comparison and MSE / PSNR metrics.
- Produce Receiver-side constellation and eye PNGs from the latest capture.

## Fixed Demo Boundary

The current demo image is fixed:

```text
source image: Transmitter\raw_pic_64.png
dimensions: 64x64
channels: RGB / 3
raw payload bytes: 12288
image frame bytes: 12297
bit count: 98376
```

Arbitrary image dimensions are not supported yet.

Reason:

- Transmitter validates/packs the current 64x64 image path.
- Receiver fallback recovery assumes fixed `64x64x3` RGB.
- Reference-image comparison uses `Transmitter\raw_pic_64.png`.

To support arbitrary dimensions later, update Transmitter image validation/packing and Receiver fallback/reference comparison together.

## Current Demo Limits

Transmitter UI, frontend JS, and backend API clamp:

```text
SNR:   6.0 .. 30.0 dB
Phase: -90 .. +90 deg
```

Reason:

- `6 dB` is already harsh enough for visual QPSK degradation.
- Lower SNR often destroys the image header rather than producing useful visual comparison.
- `-90 .. +90 deg` is used so the demo can show QPSK failing after a large absolute phase rotation while QDPSK remains recoverable under a common fixed phase offset.

Receiver analyzer is intentionally lenient. If `IMG0` is damaged, it forces fixed `64x64x3` recovery and marks `header_valid=False`.

## GUI Work Direction

The next Receiver steps are:

1. Refactor the current UDP + analysis code into a reusable background service.
2. Add a local HTTP API that exposes listener state, capture paths, and latest analysis results.
3. Build the HTML GUI on top of that API.
4. Add `pywebview` only after the browser-based GUI flow is working.
5. Add `pyinstaller` only after PC-local GUI testing and Orange Pi TX testing are complete.

The GUI should show:

- UDP listener state
- latest frame ID and capture directory
- fragment progress for QPSK and QDPSK
- recovered QPSK/QDPSK images
- MSE / PSNR
- header validity or fallback status
- QPSK/QDPSK constellation plots
- QDPSK differential constellation
- QPSK/QDPSK eye diagrams
- raw / filtered / symbol power statistics

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

Fields:

```text
magic          2 bytes   b"\xAA\xBB"
mode           uint8     0x03
version        uint8     0x01
frame_id       uint32
channel_id     uint8     0 = QPSK, 1 = QDPSK
sample_format  uint8     1 = complex64
chunk_index    uint16    0-based
chunk_count    uint16
start_sample   uint32
total_samples  uint32
chunk_samples  uint32
payload         bytes    complex64 IQ payload
```

Current default frame:

```text
sample format: complex64
bytes per sample: 8
samples per channel: 393568
UDP_FRAGMENT_PAYLOAD_BYTES: 1400
full chunk samples: 175
full datagram bytes: 1426
chunks per channel: 2249
total packets: 4498
```

Important: older project documents may mention a single-packet layout like:

```text
AA BB 03 + qpsk_len + qdpsk_len + payload
```

That is obsolete. Use the 26-byte fragmented protocol above.

## Receiver Files

Core files:

```text
Receiver\config.py
Receiver\packet.py
Receiver\frame_buffer.py
Receiver\udp_receiver.py
Receiver\main.py
Receiver\capture.py
Receiver\dsp.py
Receiver\analysis.py
Receiver\demodulation.py
Receiver\image_recovery.py
Receiver\image_output.py
Receiver\reference_image.py
Receiver\report.py
Receiver\plotter.py
```

Tools:

```text
Receiver\tools\offline_reassembly_check.py
Receiver\tools\analyze_latest_capture.py
```

Docs:

```text
Receiver\README.md
Receiver\DEVELOPMENT_LOG.md
Receiver\DEVELOPMENT_PLAN.md
Receiver\HANDOFF.md
Receiver\OVERALL_PLAN.md
```

Use `Receiver\OVERALL_PLAN.md` as the source of truth for new work. `Receiver\DEVELOPMENT_PLAN.md` is now a historical archive.

## Run Receiver

Start Receiver:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe main.py
```

Expected startup:

```text
QDPSK Receiver UDP listener
listen: 127.0.0.1:9000
header size: 26 bytes
expected sample format: complex64
waiting for UDP fragments...
```

Then start Transmitter:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe main.py
```

Open:

```text
http://127.0.0.1:8000
```

Keep target:

```text
127.0.0.1:9000
```

Click Send UDP.

Expected complete-frame output:

```text
[FRAME COMPLETE] frame_id=...
QPSK dtype: complex64 | sample count: 393568 | average power: ...
QDPSK dtype: complex64 | sample count: 393568 | average power: ...
[CAPTURE] QPSK=...\qpsk.npy, QDPSK=...\qdpsk.npy
```

## Analyze Latest Capture

Run:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Expected clean result:

```text
QPSK image: 64x64 channels=3 payload=12288 header_valid=True
QDPSK image: 64x64 channels=3 payload=12288 header_valid=True
QPSK MSE=0.000000 PSNR=inf
QDPSK MSE=0.000000 PSNR=inf
```

Expected degraded-but-useful result:

```text
QPSK image: 64x64 channels=3 payload=12288 header_valid=False
QDPSK image: 64x64 channels=3 payload=12288 header_valid=True
QPSK MSE=...
QDPSK MSE=...
```

Recovered PNGs are written beside the analyzed capture:

```text
Receiver\captures\frame_*\qpsk_recovered.png
Receiver\captures\frame_*\qdpsk_recovered.png
```

The analyzer also writes static HTML reports:

```text
Receiver\captures\frame_*\capture_report.html
Receiver\reports\latest_capture_report.html
Receiver\reports\index.html
Receiver\captures\frame_*\capture_summary.json
```

Receiver-side plot files are written beside the analyzed capture:

```text
Receiver\captures\frame_*\qpsk_rx_constellation.png
Receiver\captures\frame_*\qdpsk_rx_constellation.png
Receiver\captures\frame_*\qdpsk_diff_constellation.png
Receiver\captures\frame_*\qpsk_rx_eye.png
Receiver\captures\frame_*\qdpsk_rx_eye.png
```

## Validation Commands

Receiver compile:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
```

Offline reassembly:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\offline_reassembly_check.py
```

Analyze latest capture:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Transmitter compile if both sides are edited:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe -m py_compile config.py web_app.py tx_pipeline.py main.py
```

Frontend JS syntax if `Transmitter\static\app.js` is edited:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
node --check static\app.js
```

## Demodulation Notes

QPSK mapping used by the current Transmitter:

```text
00 ->  1 + 1j
01 -> -1 + 1j
10 -> -1 - 1j
11 ->  1 - 1j
```

This follows the actual array-index behavior in `Transmitter\modulation.py`, not necessarily older comments.

QDPSK differential demodulation:

```text
D[k] = symbol[k] * conj(symbol[k-1])
```

Decision should use phase steps nearest:

```text
0, +90, 180, -90 degrees
```

Do not treat QDPSK differential decisions as ordinary absolute QPSK quadrant decisions.

## Known Limitations

- No live Receiver GUI yet.
- Offline analyzer uses fixed timing; Gardner timing recovery is not implemented.
- Carrier synchronization and group synchronization are not implemented.
- No BER/PDF/report generation yet.
- Current fallback PNG recovery is fixed `64x64x3`.
- The project directory is not currently a Git repository from this workspace view, so use normal file inspection rather than relying on `git status`.

## Recommended Next Work

For current execution recipes and validation commands, use:

```text
Receiver\OVERALL_PLAN.md
```

Immediate next work:

1. Refactor the current UDP receive and analysis path into a background `receiver_service.py`.
2. Make the service automatically analyze each completed frame and store the latest result paths.
3. Add a local HTTP API that exposes `/api/state` and static file access for captures and reports.
4. Build the HTML GUI page that polls the API and refreshes images, plots, and metrics.
5. Add `pywebview` desktop embedding after the HTML GUI works in a browser.
6. Defer `pyinstaller` until PC-local GUI testing and Orange Pi TX testing are complete.
7. If arbitrary image sizes become required later, change both Transmitter and Receiver together:
   - Transmitter image validation/packing
   - bit count / expected sample count handling
   - Receiver fallback dimensions
   - reference-image comparison
   - documentation

## User Preferences

- Keep answers and progress updates concise.
- Use the exact Receiver interpreter above.
- Do not install dependencies automatically.
- Stop and ask the user to install missing dependencies.
- Keep Receiver work inside `Receiver\` unless explicitly allowed.
- Update Markdown when behavior or development status changes.
- The user may paste terminal logs from manual runs; those logs are useful when Codex cannot observe the live Receiver process directly.
