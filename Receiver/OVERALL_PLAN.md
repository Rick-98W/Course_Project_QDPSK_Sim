# Receiver Execution Plan

This is the current source of truth for Receiver work.

Final product target:

```text
Windows PC Receiver EXE
 -> opens an HTML-based GUI
 -> starts UDP listening automatically
 -> receives QPSK/QDPSK IQ frames from Transmitter
 -> reassembles, analyzes, demodulates, and recovers images automatically
 -> updates UI images, plots, metrics, and status whenever TX sends again
```

Do not treat the current static reports as the final product. They are useful stepping stones for the GUI.

## Read Order

1. `Receiver/HANDOFF.md`
2. `Receiver/OVERALL_PLAN.md`
3. `Receiver/README.md`
4. `Receiver/DEVELOPMENT_LOG.md` only for history

## Working Rules

1. Use `F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe` for Receiver runs.
2. Do not install dependencies automatically.
3. Keep Receiver code under `Receiver\` unless TX/RX coordination is explicitly required.
4. UDP payload is sampled `complex64` IQ, not raw image bytes and not bitstream.
5. Keep the current fragmented 26-byte header protocol.
6. Do not do PyInstaller packaging until the PC GUI is stable, TX is moved to Orange Pi, and real network testing is done.

## Current Implemented Base

Receiver already has:

- UDP fragment receive on `127.0.0.1:9000`
- 26-byte header parsing
- Fragment reassembly by `(frame_id, channel_id)`
- `.npy` capture saving
- Offline matched filtering and fixed-timing sampling
- QPSK and QDPSK demodulation
- `IMG0` image recovery and fallback recovery
- Recovered image PNG output
- MSE / PSNR comparison
- Receiver-side constellation and eye PNGs
- Matplotlib-based Chinese analysis plots using `SimHei` and `Times New Roman`
- Extra diagnostics for magnitude, phase, spectrum, and error-vector magnitude
- Static HTML reports and capture index
- Background `ReceiverService` that starts UDP listening without blocking the caller
- Thread-safe service state with latest frame, capture paths, analysis outputs, and fragment progress
- Local standard-library HTTP API on `http://127.0.0.1:9100`
- `/api/state`, `/api/start`, `/api/stop`, `/api/analyze-latest`
- Static serving for `/captures/...` and `/reports/...`
- Browser dashboard served from `/`
- Dashboard polling, image comparison, metrics, progress, and plot display
- PC-local browser GUI integration test completed
- Recommended demo runbook at `Receiver/DEMO_RUNBOOK.md`

These pieces should be reused by the GUI rather than rewritten.

## Immediate Next Step

Prepare the pywebview desktop shell.

Start with these files:

- new `desktop_app.py`
- `main.py`
- `web_app.py`

The next check must:

1. Confirm whether `pywebview` is installed in `QDRSK_RX_PC`.
2. Start Receiver backend and UDP service.
3. Open `http://127.0.0.1:9100` inside a desktop window.
4. Keep browser access available for debugging.
5. Shut down cleanly when the window closes.

The next validation command should be the smallest one that proves the backend imports:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile *.py tools\analyze_latest_capture.py
```

## Plot Diagnostics

Current generated plot set:

- `qpsk_rx_constellation.png`: QPSK 接收星座图
- `qdpsk_rx_constellation.png`: QDPSK 接收星座图
- `qdpsk_diff_constellation.png`: QDPSK 差分星座图
- `qpsk_rx_eye.png`: QPSK 接收眼图
- `qdpsk_rx_eye.png`: QDPSK 接收眼图
- `rx_magnitude.png`: 接收波形幅度
- `rx_phase.png`: 接收相位轨迹
- `rx_spectrum.png`: 接收功率谱
- `rx_evm.png`: 误差矢量幅度

Matplotlib note:

- Use low-level Matplotlib artists instead of `pyplot` / `Axes`.
- Reason: the current conda environment crashes inside `numpy.linalg.inv` / `matplotlib.transforms.get_affine` when normal Matplotlib axes are rendered.

## Final GUI Scope

The Receiver GUI should show at least:

- UDP listener status: host, port, waiting / receiving / complete / error
- Latest frame ID and capture directory
- Fragment progress for QPSK and QDPSK
- Original reference image
- QPSK recovered image
- QDPSK recovered image
- QPSK / QDPSK MSE and PSNR
- Header validity or fallback status
- QPSK RX constellation
- QDPSK RX constellation
- QDPSK differential constellation
- QPSK RX eye diagram
- QDPSK RX eye diagram
- Basic raw / filtered / symbol power statistics

Optional analysis plots after the core GUI is stable:

- Received waveform magnitude snapshot
- Raw impaired constellation before fixed symbol sampling
- PSD / spectrum estimate from received IQ
- BER estimate if TX/RX later expose reference bits cleanly
- Timing or carrier recovery diagnostic plots if sync is implemented

## Dependency Plan

Current Receiver dependencies:

- Python standard library
- NumPy

Likely GUI/runtime dependencies:

- `pywebview`: recommended desktop shell for the HTML GUI.
- WebView2 Runtime on Windows: required by pywebview's modern Windows web engine if not already installed.

Optional dependencies:

- `matplotlib`: only if the current standard-library PNG plots are not good enough.
- `websockets` or similar: only if polling is not responsive enough.
- `pyinstaller`: final packaging only, not during feature development.

Preferred first GUI implementation:

```text
Python backend + local HTML/CSS/JS + pywebview shell
```

Use polling first:

```text
JS fetches /api/state and image URLs every 0.5-1.0 sec
```

Only add WebSocket/SSE if polling becomes a real limitation.

## Development Rounds

### Round 1: Refactor Receiver Core Into Reusable Services

Goal: make the existing UDP + analysis code callable from a GUI process.

Work:

1. Keep `udp_receiver.py` as the receive engine.
2. Add or refactor a `receiver_service.py` that can start/stop the UDP listener in a background thread.
3. Store current status in a thread-safe state object.
4. When a full frame is received, save capture files and trigger analysis automatically.

Done means:

- Running the service starts listening without blocking the caller.
- A TX send produces a new capture and analysis output.
- The service exposes latest status and latest analysis paths.

Validation:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe -m py_compile *.py tools\analyze_latest_capture.py
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe tools\offline_reassembly_check.py
```

### Round 2: Add Local Receiver HTTP API

Goal: expose Receiver state and generated files to HTML.

Work:

1. Add `web_app.py` using the standard library first.
2. Add APIs:
   - `GET /`
   - `GET /api/state`
   - `POST /api/start`
   - `POST /api/stop`
   - `POST /api/analyze-latest`
   - `GET /captures/...`
   - `GET /reports/...`
3. Serve static HTML/CSS/JS from `templates/` and `static/`.

Done means:

- Browser can load the Receiver page.
- `/api/state` returns listener state, progress, latest metrics, and latest image/plot URLs.
- Sending from TX updates backend state without restarting the page.

Validation:

```powershell
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe main.py
```

Then open the local URL and confirm `/api/state` changes after a TX send.

### Round 3: Build HTML GUI

Goal: make the first usable PC Receiver dashboard.

Work:

1. Add `templates/index.html`.
2. Add `static/app.js`.
3. Add `static/style.css`.
4. Display live status, fragment progress, recovered images, plots, and metrics.
5. Poll `/api/state` periodically and refresh image URLs with cache-busting.

Done means:

- User starts Receiver once.
- UDP listener starts automatically.
- User sends from TX.
- GUI updates without manual analyzer command.
- TX sends again and GUI updates again.

### Round 4: Integrate pywebview Shell

Goal: make the Receiver feel like a desktop app while still using HTML GUI.

Work:

1. Add `desktop_app.py` or equivalent entry point.
2. Start backend and UDP service.
3. Open the local Receiver page inside pywebview.
4. Keep browser debugging possible during development.

Done means:

- Running one Python command opens the GUI window.
- UDP listener starts automatically.
- TX sends update the window.
- Closing the window shuts down the backend cleanly.

Dependency required for this round:

```text
pywebview
```

Windows runtime requirement:

```text
Microsoft Edge WebView2 Runtime
```

### Round 5: PC Local End-To-End GUI Test

Goal: verify the complete PC-local user workflow.

Work:

1. Start Receiver GUI.
2. Start Transmitter on the same PC.
3. Send multiple frames with different SNR / phase.
4. Confirm the Receiver GUI updates each time.
5. Confirm QPSK and QDPSK differences are visible and metrics update.

Done means:

- No manual analyzer command is required.
- No page refresh is required.
- New TX frames replace the displayed latest result automatically.

### Round 6: Orange Pi TX Migration And Network Test

Goal: move TX to Orange Pi and prove Receiver GUI works over the real demo network.

Work:

1. Keep Receiver on Windows PC.
2. Move Transmitter to Orange Pi.
3. Put both devices on the same network.
4. Point TX target IP to the PC Receiver IP and port.
5. Send multiple frames and verify Receiver GUI updates.

Done means:

- Receiver GUI receives Orange Pi frames.
- Image recovery and plots update automatically.
- Packet loss or firewall issues are understood and documented.

### Round 7: Final Packaging Prep

Goal: prepare for exe packaging only after the runtime behavior is stable.

Work:

1. Freeze dependency versions.
2. Add a packaging entry point.
3. Add PyInstaller spec only after the GUI workflow is stable.
4. Include templates, static files, and runtime assets.
5. Test packaged app on the target Windows machine.

Dependency required for this round:

```text
pyinstaller
```

Done means:

- Double-clicking the exe opens Receiver GUI.
- UDP listener starts automatically.
- TX sends update the packaged app.
- No conda terminal is required for normal demo use.

## Stop Criteria

Receiver can be considered finished for the current course demo when:

1. Double-click or one-command Receiver GUI starts successfully.
2. UDP listener starts automatically.
3. TX can send repeatedly and Receiver updates each time.
4. GUI shows original image, QPSK recovered image, QDPSK recovered image, plots, metrics, and receive status.
5. PC-local test passes.
6. Orange Pi TX to PC RX network test passes.
7. EXE packaging passes only after the above are stable.

## Deferred Work

Do not do these before the GUI workflow is complete:

- Gardner timing recovery
- Carrier recovery
- Group synchronization
- Arbitrary image dimensions
- `int16` IQ transport
- PDF export
- PyInstaller packaging
