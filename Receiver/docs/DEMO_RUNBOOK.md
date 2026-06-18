# Receiver Demo Runbook

This demo is local or LAN-only. It does not require internet access.

## Start Receiver

Desktop app:

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

## Start Transmitter

```powershell
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe main.py
```

Open:

```text
http://127.0.0.1:8000
```

For PC-local testing, keep TX target:

```text
127.0.0.1:9000
```

For phone-hotspot LAN testing:

1. Connect the Windows PC and Orange Pi to the same phone hotspot.
2. Start the Receiver desktop app on the PC.
3. In the Receiver dashboard, read `TX 目标地址`.
4. Open the Transmitter page on the Orange Pi.
5. Set the TX UDP target to that value, usually:

```text
192.168.x.x:9000
```

6. Confirm TX has loaded the fixed `Transmitter/raw_pic_64.png` source image.
7. Click `Send UDP`.
8. Confirm TX reports that the reference image was sent to RX.

The reference-image upload uses the same host and port `9100`, for example:

```text
http://192.168.x.x:9100/api/reference-image
```

The phone does not need mobile data or internet access. It only needs to provide the local Wi-Fi network between the two devices.

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
