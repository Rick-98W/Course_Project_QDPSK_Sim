# QDPSK Receiver

This directory is the isolated Python receiver project.

Current execution plan:

```text
Receiver/OVERALL_PLAN.md
```

PC-local demo runbook:

```text
Receiver/DEMO_RUNBOOK.md
```

`DEVELOPMENT_PLAN.md` is historical and should not be used as the source of truth for new work.
Current Receiver target is an HTML-based GUI desktop app that auto-listens on UDP and refreshes results whenever TX sends again. Static reports are only the current stepping stone.

Use this interpreter for Receiver work:

```text
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe
```

Do not install dependencies automatically. If a package is missing, stop and ask the user to install it in conda.

Current scope:

- Listen on UDP `127.0.0.1:9000`.
- Serve a local HTTP API on `http://127.0.0.1:9100`.
- Expose live Receiver service state at `GET /api/state`.
- Parse the current 26-byte application header from `Transmitter/packet.py`.
- Collect fragments by `(frame_id, channel_id)`.
- Reassemble QPSK and QDPSK payloads into `np.complex64` IQ arrays.
- Print dtype, sample count, and average power for each complete channel.
- Save complete QPSK and QDPSK IQ arrays as `.npy` captures.

The receiver now includes offline capture analysis for matched filtering, hard-decision demodulation, and image-frame recovery.
The analyzer uses strict `IMG0` parsing when possible. If low SNR or heavy phase rotation damages the header, it falls back to fixed 64x64 RGB recovery so a degraded PNG is still produced.
Those offline outputs are now feeding the planned HTML GUI.

## Run

Start Receiver first:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe main.py
```

Receiver starts the UDP listener and local HTTP API together.

Open the Receiver dashboard:

```text
http://127.0.0.1:9100
```

Raw JSON state:

```text
http://127.0.0.1:9100/api/state
```

Then start Transmitter:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
python main.py
```

Open the Transmitter page:

```text
http://127.0.0.1:8000
```

Keep the UDP target as:

```text
127.0.0.1:9000
```

Click `Send UDP`. Receiver should collect both channels and print:

```text
QPSK dtype: complex64 | sample count: 393568 | average power: ...
QDPSK dtype: complex64 | sample count: 393568 | average power: ...
```

Completed frames are saved under:

```text
C:\Users\Rick\PycharmProjects\QDPSK\Receiver\captures
```

Each complete frame gets its own timestamped directory with:

```text
qpsk.npy
qdpsk.npy
```

Disable capture writing by setting this in `config.py`:

```python
SAVE_COMPLETED_FRAMES = False
```

Analyze the latest capture:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Expected output includes raw sample count, matched-filter sample count, fixed-timing symbol count, and symbol power for both channels.

It also prints recovered `IMG0` frame sizes when demodulation succeeds.
Recovered PNG files are written beside the analyzed capture:

```text
qpsk_recovered.png
qdpsk_recovered.png
```

The same command also prints MSE and PSNR against `Transmitter/raw_pic_64.png`.
When fallback recovery is used, the output includes `header_valid=False`.

The analyzer also writes a static comparison report and browsing index:

```text
captures/frame_*/capture_report.html
reports/latest_capture_report.html
```

The report shows the original image, recovered QPSK image, recovered QDPSK image, and the main MSE / PSNR metrics.

It also writes Receiver-side communication plots beside the analyzed capture:

```text
qpsk_rx_constellation.png
qdpsk_rx_constellation.png
qdpsk_diff_constellation.png
qpsk_rx_eye.png
qdpsk_rx_eye.png
```

An index page is also generated at:

```text
reports/index.html
```

The final GUI will reuse the same recovered PNGs, plots, and metrics, but it will display them live in an HTML dashboard instead of requiring manual analyzer runs.

The current browser dashboard already polls `/api/state` and displays:

- UDP listener state
- latest frame ID and capture directory
- QPSK / QDPSK fragment progress
- original / QPSK / QDPSK image comparison
- MSE / PSNR and header status
- raw / filtered / symbol power statistics
- Receiver-side constellation, eye, magnitude, phase, spectrum, and EVM plots

Generated files can also be served by the local Receiver API:

```text
http://127.0.0.1:9100/captures/...
http://127.0.0.1:9100/reports/...
```

## Protocol Boundary

UDP payload is not raw image bytes and not a bitstream. It is sampled digital baseband IQ after RRC shaping and channel impairment.

Current transport format:

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

## Current Image Constraint

As of 2026-06-15, the demo image source is fixed to:

```text
Transmitter/raw_pic_64.png
64x64 RGB
raw payload bytes = 12288
image frame bytes = 12297
```

The receiver analyzer can parse `IMG0` width and height when the header is valid, but its degraded-channel fallback intentionally assumes fixed `64x64x3` RGB. Arbitrary image sizes are not supported yet and require coordinated Transmitter and Receiver changes.
