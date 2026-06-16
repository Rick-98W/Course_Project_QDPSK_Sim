# Receiver Demo Runbook

This demo is local or LAN-only. It does not require internet access.

## Start Receiver

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Receiver
F:\programs\miniconda3\envs\QDRSK_RX_PC\python.exe main.py
```

Open:

```text
http://127.0.0.1:9100
```

## Start Transmitter

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe main.py
```

Open:

```text
http://127.0.0.1:8000
```

Keep TX target:

```text
127.0.0.1:9000
```

## Recommended PC-Local Demo Cases

Use these in order:

```text
SNR=30 dB, Phase=0 deg
```

Expected: QPSK and QDPSK both recover well.

```text
SNR=30 dB, Phase=75 deg
```

Expected: QPSK fails from absolute phase quadrant error; QDPSK remains recoverable.

```text
SNR=6 dB, Phase=0 deg
```

Expected: noise effects may appear; QDPSK can show small differential-detection loss.

```text
SNR=6 dB, Phase=90 deg
```

Expected: QPSK is dominated by phase ambiguity; QDPSK cancels the fixed phase rotation and should remain recoverable unless noise causes incidental errors.

## Verified Local Result - 2026-06-16

Observed via TX API sends and RX `/api/state`:

```text
SNR=30 dB, Phase=75 deg:
  QPSK MSE=19219.832682, PSNR=5.293 dB, header_valid=False
  QDPSK MSE=0.000000, PSNR=inf, header_valid=False

SNR=6 dB, Phase=90 deg:
  QPSK MSE=19219.832682, PSNR=5.293 dB, header_valid=False
  QDPSK MSE=0.000000, PSNR=inf, header_valid=False
```

Note: `header_valid=False` can still produce a correct or useful recovered image because Receiver fallback forces fixed `64x64x3` RGB recovery for this demo image.
