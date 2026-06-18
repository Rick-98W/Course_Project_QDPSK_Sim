# Orange Pi Transmitter Migration Notes

This document records what is needed to move the Transmitter side from the
Windows development PC to an Orange Pi running Ubuntu 22.04.

## Conclusion

The Transmitter project is close to copy-and-run, but it is not completely
environment-free.

Copy the whole `Transmitter/` folder to the Orange Pi, then run it inside a
Linux/ARM conda environment with the required Python packages and fonts
installed.

Do not copy the Windows conda environment. A Windows conda environment cannot
run on Ubuntu ARM.

## What To Copy

Copy this folder:

```text
Transmitter/
```

Required contents:

```text
Transmitter/
  main.py
  config.py
  raw_pic_64.png
  README.md
  docs/
  core/
  analysis/
  web/
```

Optional / generated contents that do not need to be copied:

```text
Transmitter/.idea/
Transmitter/__pycache__/
Transmitter/web/static/generated/
```

`web/static/generated/` is recreated at runtime when TX renders plots.

## Orange Pi Environment

Target OS:

```text
Ubuntu 22.04
```

Python:

```text
Python 3.10.x is acceptable.
```

The built-in Ubuntu Python may work, but the recommended route is:

```text
Install conda on Orange Pi.
Create a fresh Linux/ARM conda environment.
Install TX dependencies inside that environment.
```

Current required Python packages:

```text
numpy
matplotlib
```

No Pillow dependency is currently required. The fixed PNG source image is parsed
by project code.

## Font Requirements

TX HTML and Matplotlib output are intended to preserve:

```text
Chinese: SimHei
English/numbers: Times New Roman
```

Ubuntu usually does not include these fonts by default.

If the fonts are missing, TX may still run, but Matplotlib and Chromium can fall
back to other fonts and the generated figures will not match the desired style.

Before the final demo, verify that the Orange Pi has usable equivalents for:

```text
SimHei
Times New Roman
```

If exact fonts are unavailable, install/copy the font files and refresh the Linux
font cache.

## How To Run On Orange Pi

From the Orange Pi terminal:

```bash
cd /path/to/Transmitter
python main.py
```

Then open Chromium on the Orange Pi:

```text
http://127.0.0.1:8000
```

Do not open `web/templates/index.html` directly. The page needs the Python HTTP
server for APIs, static files, image loading, plot generation, and UDP sending.

## LAN Demo Topology

Final intended topology:

```text
Phone hotspot LAN
  PC Receiver
  Orange Pi Transmitter
```

The phone hotspot only provides a local network. It does not need mobile data or
internet access.

Communication paths:

```text
Orange Pi TX web page: local Chromium -> http://127.0.0.1:8000
TX -> RX UDP IQ stream: UDP <PC_RX_IP>:9000
TX -> RX reference image: HTTP POST http://<PC_RX_IP>:9100/api/reference-image
TX -> RX TX plots zip: HTTP POST http://<PC_RX_IP>:9100/api/tx-plots
```

HTTP is only a local communication mechanism between the two project endpoints.
There is no online service.

## LAN Test Procedure

1. Start Receiver on the Windows PC.
2. Connect both the Windows PC and Orange Pi to the same phone hotspot.
3. In the RX GUI, read the displayed TX target address, normally like:

```text
192.168.x.x:9000
```

4. Start TX on the Orange Pi:

```bash
cd /path/to/Transmitter
python main.py
```

5. Open Orange Pi Chromium:

```text
http://127.0.0.1:8000
```

6. In the TX page, set:

```text
target host = PC RX IP
target port = 9000
```

7. Send the standard demo cases:

```text
30 dB, 0 deg
30 dB, 75 deg
6 dB, 0 deg
6 dB, 90 deg
-3 dB harsh-noise cases
```

8. Confirm RX receives:

```text
QPSK/QDPSK UDP IQ frames
reference image
10 TX-side plot PNGs
RX-side recovered images and analysis plots
Markdown export with recovered images, RX plots, and TX plots
```

## Common Failure Points

If TX starts but RX does not update:

```text
Check TX target host is the PC RX LAN IP, not 127.0.0.1.
Check TX target port is 9000.
Check PC and Orange Pi are on the same hotspot.
Check Windows Firewall allows inbound UDP 9000.
Check Windows Firewall allows inbound TCP 9100.
Check no stale old Python processes occupy 8000 / 9000 / 9100.
```

If TX page does not load:

```text
Run python main.py from the Transmitter directory.
Open http://127.0.0.1:8000 in Orange Pi Chromium.
Do not open the HTML file directly.
Check whether port 8000 is already occupied.
```

If plots render with wrong fonts:

```text
Install or copy SimHei and Times New Roman fonts on Orange Pi.
Refresh font cache.
Restart TX.
Regenerate plots.
```

If Python import errors occur:

```text
Make sure the command is run from /path/to/Transmitter.
Make sure core/, analysis/, and web/ were copied.
Make sure __init__.py files were copied.
Install missing packages in the Orange Pi conda environment.
```

## Current Assessment

The TX code itself is already organized with relative paths based on
`Transmitter/config.py`, so it should not depend on the original Windows project
path.

Expected remaining migration work:

```text
1. Create Orange Pi conda environment.
2. Install numpy and matplotlib.
3. Install or verify SimHei and Times New Roman fonts.
4. Copy Transmitter/.
5. Run python main.py on Orange Pi.
6. Open http://127.0.0.1:8000 in Chromium.
7. Perform PC RX + Orange Pi TX LAN test over phone hotspot.
8. Resolve firewall/IP/font issues if they appear.
```
