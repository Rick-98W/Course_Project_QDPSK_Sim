# Receiver Development Log

## 2026-06-15 Round 1-4: UDP receive and IQ reassembly

Status: completed.

Runtime environment:

```text
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe
```

Dependency policy:

- Do not auto-install packages.
- If a dependency is missing, stop and tell the user to install it in conda.

Implemented files:

```text
config.py
packet.py
frame_buffer.py
udp_receiver.py
main.py
README.md
```

Scope completed:

- UDP listener entry point at `python main.py`.
- Default bind target: `127.0.0.1:9000`.
- Current 26-byte application header parser using:

```python
struct.Struct(">2sBBIBBHHIII")
```

- Protocol validation:

```text
magic == b"\xAA\xBB"
mode == 0x03
version == 0x01
sample_format == 1
channel_id in {0, 1}
payload_bytes % 8 == 0
chunk_samples == payload_bytes / 8
```

- Fragment collection by:

```text
(frame_id, channel_id)
```

- Out-of-order fragment reassembly by `chunk_index`.
- Duplicate fragment counting.
- Metadata conflict checks for `chunk_count` and `total_samples`.
- Full-frame IQ reconstruction as `np.complex64`.
- Summary output for each completed frame:

```text
QPSK dtype: complex64 | sample count: ... | average power: ...
QDPSK dtype: complex64 | sample count: ... | average power: ...
```

Validation performed:

```powershell
python -m py_compile config.py packet.py frame_buffer.py udp_receiver.py main.py
```

Result: passed.

Offline reassembly test:

- Created synthetic QPSK and QDPSK complex64 fragments.
- Fed fragments in shuffled order.
- Confirmed both channels reassembled in correct `chunk_index` order.
- Confirmed final arrays are `complex64` with expected sample order.

Live receiver result reported by user:

- First datagram received from `127.0.0.1`.
- Header parsed correctly.
- Both QPSK and QDPSK frames progressed through fragment collection.
- This confirms the current receiver path is working up to fragment reassembly and runtime progress reporting.

Next step:

Run live PC-local TX/RX integration:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
python main.py
```

In another terminal:

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
python main.py
```

Open:

```text
http://127.0.0.1:8000
```

Keep Transmitter target:

```text
127.0.0.1:9000
```

Click `Send UDP`.

Expected live result:

```text
QPSK dtype: complex64 | sample count: 393568 | average power: ...
QDPSK dtype: complex64 | sample count: 393568 | average power: ...
```

## 2026-06-15 Round 6: completed-frame capture files

Status: completed.

Implemented files:

```text
capture.py
tools/offline_reassembly_check.py
```

Updated files:

```text
config.py
udp_receiver.py
README.md
DEVELOPMENT_PLAN.md
DEVELOPMENT_LOG.md
```

Scope completed:

- Added `SAVE_COMPLETED_FRAMES` and `CAPTURE_DIR` to `config.py`.
- When both QPSK and QDPSK channels are complete, Receiver saves the arrays as `.npy`.
- Capture output directory:

```text
captures/frame_<frame_id>_<timestamp>/
  qpsk.npy
  qdpsk.npy
```

- Added an offline sanity check for parsing, out-of-order reassembly, and `.npy` roundtrip.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py udp_receiver.py main.py tools\offline_reassembly_check.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\offline_reassembly_check.py
```

Result:

```text
offline reassembly check passed
```

Dependency note:

- `numpy` is available in `QDRSK_RX_PC`.
- No dependencies were installed automatically.

## 2026-06-15 Round 5-6 live integration note

Observed from real run under `QDRSK_RX_PC`:

- UDP listener starts correctly and parses the first datagram/header.
- QPSK and QDPSK progress logs advance in parallel.
- The run shown so far did not reach the complete-frame summary line yet.

Inference:

- The current receiver path is alive.
- The missing complete-frame output is likely due to either burst loss on the Windows loopback receive path or the transmitter run not finishing both channels in that specific attempt.
- To make this easier to diagnose, the receiver now raises `SO_RCVBUF` and prints idle diagnostics when no packets arrive for a short period.

Follow-up live result reported by user:

```text
QPSK chunks=2249/2249
QDPSK chunks=2249/2249
QPSK dtype: complex64 | sample count: 393568 | average power: 0.126467
QDPSK dtype: complex64 | sample count: 393568 | average power: 0.126341
```

Capture files were written successfully under `captures/frame_0761311767_.../`.

## 2026-06-15 Round 7: matched filter and fixed-timing sampling

Status: base version completed.

Implemented files:

```text
dsp.py
analysis.py
tools/analyze_latest_capture.py
```

Scope completed:

- Recreated Receiver-side RRC tap generation with the same parameters as Transmitter.
- Added matched filtering for completed IQ captures.
- Added fixed-timing symbol sampling using total TX+RX RRC delay.
- Added latest-capture analysis entry point.

Validation performed with:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py udp_receiver.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Observed result:

```text
QPSK raw=393568 power=0.126467 filtered=393632 filtered_power=0.916570 symbols=49196 symbol_power=1.004813
QDPSK raw=393568 power=0.126341 filtered=393632 filtered_power=0.909426 symbols=49196 symbol_power=1.003129
```

Notes:

- Symbol power near 1 indicates the fixed sampling path is aligned well enough for the next demodulation step.
- Gardner timing recovery is not implemented yet.

## 2026-06-15 Round 8: hard-decision demodulation scaffold

Status: completed.

Implemented files:

```text
demodulation.py
image_recovery.py
tools/analyze_latest_capture.py
```

Scope added:

- QPSK Gray hard decision.
- QDPSK differential hard decision.
- Bit packing back to bytes.
- Fixed transmitter image frame parsing.

Note:

- The first pass uses fixed-timing sampled symbols from the latest capture.
- If the reconstructed bitstream does not yet parse as `IMG0`, that will be diagnosed in the next validation pass and likely requires better timing recovery or a small symbol-offset sweep.

Validation follow-up:

- QPSK recovered `IMG0` successfully from the latest capture.
- QDPSK recovered `IMG0` successfully from the latest capture.

Observed parse result:

```text
QPSK image: 64x64 channels=3 payload=12288
QDPSK image: 64x64 channels=3 payload=12288
```

## 2026-06-15 Round 9: recovered image output and quality metrics

Status: completed.

Implemented files:

```text
reference_image.py
image_output.py
```

Updated files:

```text
config.py
tools/analyze_latest_capture.py
README.md
DEVELOPMENT_PLAN.md
DEVELOPMENT_LOG.md
```

Scope completed:

- Load `Transmitter/raw_pic_64.png` as the reference RGB image.
- Save recovered QPSK and QDPSK RGB payloads as PNG files beside the capture.
- Compute MSE and PSNR against the reference RGB payload.

Validation performed with:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py udp_receiver.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Observed result:

```text
QPSK image: 64x64 channels=3 payload=12288
QDPSK image: 64x64 channels=3 payload=12288
QPSK MSE=0.000000 PSNR=inf
QDPSK MSE=0.000000 PSNR=inf
```

Recovered files:

```text
captures/frame_.../qpsk_recovered.png
captures/frame_.../qdpsk_recovered.png
```

## 2026-06-15 Round 10: lenient image recovery for degraded channels

Status: completed.

Scope:

- The analyzer now uses strict `IMG0` parsing when possible.
- If low SNR or heavy phase rotation damages the image header, it falls back to a fixed 64x64 RGB recovery path.
- This keeps the visual comparison meaningful even when the frame header is broken.

Validation note:

- Latest analyzer run produced a fallback QPSK image with `header_valid=False`.
- QDPSK still recovered cleanly.

## 2026-06-15 Round 11: documentation and fixed image boundary

Status: documentation synchronized.

Current boundary:

- The live demo image remains fixed at `64x64 RGB`.
- `Transmitter/raw_pic_64.png` is the only supported source image in the current implementation.
- Receiver strict image recovery accepts valid `IMG0` metadata.
- Receiver fallback recovery is intentionally fixed to `64x64x3` so noisy frames still produce a comparable degraded PNG.
- Arbitrary image dimensions are not supported yet; they require coordinated transmitter packing, receiver fallback sizing, and reference-image comparison changes.

Demo parameter policy:

- Transmitter UI and backend clamp SNR to `6.0 .. 30.0 dB`.
- Transmitter UI and backend now clamp phase rotation to `-90 .. +90 deg`.
- The limits keep the visual demo harsh enough to show QPSK degradation while avoiding mostly unrecoverable image-header failures.

## 2026-06-15 Round 12: receiver-side communication plots and HTML report

Status: completed.

Implemented files:

```text
plotter.py
report.py
```

Updated files:

```text
analysis.py
tools/analyze_latest_capture.py
README.md
HANDOFF.md
```

Scope completed:

- Added a pure-standard-library PNG plot renderer for Receiver capture analysis.
- Generated receiver-side QPSK constellation plots from matched-filter fixed-timing symbols.
- Generated receiver-side QDPSK constellation plots from matched-filter fixed-timing symbols.
- Generated receiver-side QDPSK differential constellation plots using `symbol[k] * conj(symbol[k-1])`.
- Generated receiver-side eye diagrams from matched-filter IQ magnitude traces.
- Extended the static HTML report to include the new communication plots.
- Kept the existing image recovery and MSE / PSNR comparison flow intact.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Result:

```text
capture_report.html generated successfully
reports/latest_capture_report.html generated successfully
receiver-side constellation and eye PNGs generated beside the capture
```

## 2026-06-15 Round 13: capture report index

Status: completed.

Scope completed:

- Analyzer now writes `capture_summary.json` beside each analyzed capture.
- Analyzer now refreshes `Receiver/reports/index.html`.
- The index page lists analyzed captures, QPSK/QDPSK MSE and PSNR, header status, and links to each capture's static report.
- Existing `Receiver/reports/latest_capture_report.html` remains the direct latest-report shortcut.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Result:

```text
reports/index.html generated successfully
capture_summary.json generated beside the latest analyzed capture
```

## 2026-06-15 Round 14: overall plan document

Status: completed.

Scope completed:

- Added `OVERALL_PLAN.md` as the current step-by-step Receiver plan.
- Kept the historical `DEVELOPMENT_PLAN.md` intact.
- Pointed `README.md`, `HANDOFF.md`, and `DEVELOPMENT_PLAN.md` at the new plan entry point.
- Based the new plan on the existing Receiver docs and current implemented state.

Validation performed:

- Confirmed the new plan exists and the entry-point references are present in the key Markdown files.

## 2026-06-15 Round 15: planning doc cleanup

Status: completed.

Scope completed:

- Rewrote `OVERALL_PLAN.md` into an execution-oriented recipe document.
- Downgraded `DEVELOPMENT_PLAN.md` to a historical archive.
- Updated `README.md` and `HANDOFF.md` so they point to `OVERALL_PLAN.md` as the source of truth.

Validation performed:

- Confirmed the main Receiver Markdown files now point to the execution plan instead of the archived plan.

## 2026-06-15 Round 16: GUI target reset

Status: completed.

Scope completed:

- Updated `OVERALL_PLAN.md` to make the HTML GUI the real Receiver target.
- Clarified that static reports are only a stepping stone, not the final product.
- Updated `HANDOFF.md` and `README.md` so they describe the GUI / auto-listen / auto-refresh workflow.
- Kept `DEVELOPMENT_PLAN.md` as a historical archive only.

Current next implementation step:

- Refactor the existing UDP + analysis path into a background Receiver service that can feed the HTML GUI and later the desktop shell.

## 2026-06-15 Round 17: background receiver service

Status: completed.

Scope completed:

- Added `receiver_service.py` as a background wrapper around the existing UDP receive path.
- Extended `udp_receiver.py` with optional callbacks and a stop event so the receive loop can run under a service without breaking the CLI path.
- Moved latest-capture analysis into reusable functions in `analysis.py`.
- Simplified `tools/analyze_latest_capture.py` to call the shared analysis entry point.
- Updated `main.py` to start the Receiver service instead of calling the blocking UDP loop directly.
- Added thread-safe service state for listener status, latest frame, capture paths, analysis outputs, and per-channel progress.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py receiver_service.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\offline_reassembly_check.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\analyze_latest_capture.py
```

Service smoke test:

```text
listen_port=19000 -> status=listening -> stopped
```

Note:

- Default port `9000` was already occupied during the smoke test, so the service was validated on a temporary port.

## 2026-06-16 Round 18: Matplotlib receiver plots and extra diagnostics

Status: completed.

Scope completed:

- Replaced the hand-written standard-library PNG plot renderer in `plotter.py` with Matplotlib-based rendering.
- Configured plot text to use `SimHei` for Chinese labels and `Times New Roman` for numeric tick labels.
- Converted plot titles, legends, axis labels, and report plot captions to Chinese.
- Kept existing plot outputs:
  - QPSK 接收星座图
  - QDPSK 接收星座图
  - QDPSK 差分星座图
  - QPSK 接收眼图
  - QDPSK 接收眼图
- Added diagnostic plots:
  - 接收波形幅度
  - 接收相位轨迹
  - 接收功率谱
  - 误差矢量幅度

Implementation note:

- Normal Matplotlib `pyplot` / `Axes` rendering crashes in this conda environment inside `numpy.linalg.inv` / `matplotlib.transforms.get_affine`.
- The current renderer therefore uses Matplotlib low-level artists on manual pixel coordinates and avoids `Axes`, ticks, and patches.
- This keeps the plots generated by Matplotlib while avoiding the known native crash path.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py receiver_service.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -X faulthandler tools\analyze_latest_capture.py
```

Result:

```text
Generated recovered image PNGs plus 9 analysis plot PNGs beside the latest capture.
```

## 2026-06-16 Round 19: local HTTP API

Status: completed.

Scope completed:

- Added `web_app.py` using the Python standard library `http.server`.
- Added `GET /` as a temporary browser status page.
- Added `GET /api/state` returning `ReceiverService.snapshot()` as JSON.
- Added `POST /api/start`.
- Added `POST /api/stop`.
- Added `POST /api/analyze-latest`.
- Added static file access for:
  - `/captures/...`
  - `/reports/...`
- Updated `main.py` so one command starts both:
  - UDP Receiver service on `127.0.0.1:9000`
  - HTTP API on `http://127.0.0.1:9100`
- Updated `README.md` with the new run and API URLs.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py receiver_service.py web_app.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
```

HTTP smoke tests:

```text
GET http://127.0.0.1:19100/api/state -> 200 JSON
GET http://127.0.0.1:19101/reports/index.html -> 200 text/html
```

Note:

- Smoke tests used temporary ports to avoid conflicts with any live demo process.

## 2026-06-16 Round 20: browser dashboard

Status: completed.

Scope completed:

- Added `templates/index.html` as the first Receiver dashboard.
- Added `static/style.css` for the dashboard layout.
- Added `static/app.js` for polling `/api/state` and refreshing assets.
- Updated `web_app.py` to serve:
  - `/`
  - `/static/...`
  - `/reference-image`
  - `/captures/...`
  - `/reports/...`
- Extended `/api/state` responses with `latest_asset_urls` so the frontend can load generated files without parsing Windows filesystem paths.
- Dashboard currently shows:
  - UDP listener state
  - latest frame ID
  - capture directory
  - QPSK / QDPSK fragment progress
  - original image
  - QPSK / QDPSK recovered images
  - MSE / PSNR
  - header valid / fallback status
  - raw / filtered / symbol power metrics
  - 9 Receiver-side analysis plots
- Added start / stop / analyze-latest controls for development use.

Validation performed with the required Receiver interpreter:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile config.py packet.py frame_buffer.py capture.py dsp.py analysis.py demodulation.py image_recovery.py image_output.py reference_image.py report.py plotter.py udp_receiver.py receiver_service.py web_app.py main.py tools\offline_reassembly_check.py tools\analyze_latest_capture.py
node --check static\app.js
```

HTTP smoke tests:

```text
GET / -> 200 text/html
GET /static/style.css -> 200 text/css
GET /static/app.js -> 200 text/javascript
GET /reference-image -> 200 image/png
GET /api/state -> 200 application/json
```

Asset URL validation:

```text
latest_asset_urls.qpsk_recovered -> /captures/frame_.../qpsk_recovered.png
```

## 2026-06-16 Round 21: PC-local end-to-end GUI test

Status: completed.

Scope completed:

- Started Receiver service and dashboard on:
  - UDP `127.0.0.1:9000`
  - HTTP `http://127.0.0.1:9100`
- Started Transmitter on `http://127.0.0.1:8000`.
- Drove Transmitter through local HTTP API.
- Confirmed Receiver `/api/state` updates after TX sends.
- Confirmed latest asset URLs are exposed for the dashboard:
  - `qpsk_recovered`
  - `qdpsk_recovered`
  - Receiver analysis plots
- Added `DEMO_RUNBOOK.md` with the recommended local demo procedure.

Validated key phase-rotation demo cases:

```text
SNR=30 dB, Phase=75 deg:
  QPSK MSE=19219.832682, PSNR=5.293 dB, header_valid=False
  QDPSK MSE=0.000000, PSNR=inf, header_valid=False

SNR=6 dB, Phase=90 deg:
  QPSK MSE=19219.832682, PSNR=5.293 dB, header_valid=False
  QDPSK MSE=0.000000, PSNR=inf, header_valid=False
```

Interpretation:

- High-SNR large phase rotation shows the intended QDPSK advantage.
- QPSK fails from absolute phase quadrant ambiguity.
- QDPSK cancels a fixed common phase rotation through differential detection.
