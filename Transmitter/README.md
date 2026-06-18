# QDPSK Transmitter

This is the transmitter-side Python project.

Project notes and historical development logs are under:

```text
Transmitter/docs/
```

Orange Pi migration notes:

```text
Transmitter/docs/ORANGE_PI_MIGRATION.md
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

Do not open `web/templates/index.html` directly. The page needs the Python HTTP API for fixed image serving, plot generation, reference-image sync, and UDP sending.

## Current Workflow

1. Open the TX web page.
2. TX immediately loads the fixed source image:

```text
Transmitter/raw_pic_64.png
```

3. TX renders the channel-pre reference plots.
4. Click `Send UDP`.
5. TX uploads the fixed reference PNG to RX:

```text
POST http://<target_host>:<target_port + 100>/api/reference-image
```

For the default UDP target `127.0.0.1:9000`, the reference upload target is:

```text
http://127.0.0.1:9100/api/reference-image
```

6. TX applies SNR / phase, renders channel-post plots, fragments the `complex64` IQ, and sends UDP packets.

## Plot Naming

Use `信道前` instead of `干净`.

```text
信道前基带功率谱   transmitter-side reference, not affected by SNR / phase
信道前基带眼图     transmitter-side reference, not affected by SNR / phase
信道前星座图       transmitter-side reference, not affected by SNR / phase
信道后星座图       rendered after Send UDP, affected by SNR / phase
信道后眼图         rendered after Send UDP, affected by SNR / phase
```

The PNG filenames are kept stable for now:

```text
qpsk_psd.png
qdpsk_psd.png
qpsk_eye.png
qdpsk_eye.png
qpsk_constellation.png
qdpsk_constellation.png
qpsk_impaired_constellation.png
qdpsk_impaired_constellation.png
qpsk_impaired_eye.png
qdpsk_impaired_eye.png
```

## Defaults

```text
TARGET_HOST = 127.0.0.1
TARGET_PORT = 9000
WEB_HOST = 0.0.0.0
WEB_PORT = 8000
SNR_DB = 20.0
PHASE_DEG = 0.0
SNR range = -3.0 .. 30.0 dB
Phase range = -90 .. +90 deg
```

The page can change UDP target IP, target port, SNR, and phase at runtime. These runtime edits are not written back to `config.py`.

## Boundaries

- The fixed source image must be a `64x64` RGB PNG at `Transmitter/raw_pic_64.png`.
- UDP sends sampled digital baseband `complex64` IQ after RRC shaping and channel impairment.
- UDP does not send raw image bytes.
- UDP does not send the bitstream directly.
- QPSK and QDPSK are generated and sent together.
