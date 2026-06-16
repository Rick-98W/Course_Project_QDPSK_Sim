# QDPSK Transmitter

本目录是 QDPSK 课程设计的发射端工程。当前阶段只负责 Transmitter。

## 运行方式

在 PowerShell 或 PyCharm Terminal 中运行：

```powershell
conda activate QDRSK_TX_ELB
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
python main.py
```

然后在浏览器打开：

```text
http://127.0.0.1:8000
```

不要直接双击 `templates/index.html`。HTML 页面需要 Python HTTP 服务提供 API、图片和 UDP 发送逻辑。

## 当前功能

- 读取 `raw_pic_64.png`
- 构造 `IMG0` 图像帧
- 转 bitstream
- 同时生成 QPSK / QDPSK 两路符号
- RRC 基带成型
- 对两路波形施加相同 SNR 和 Phase
- 生成页面图表
- 按 `complex64` 采样级 IQ 分片 UDP 发送

## 页面图表

页面左列是 QPSK，右列是 QDPSK。

```text
信道后星座图     会随 SNR / Phase 改变
信道后眼图       会随 SNR / Phase 改变
干净基带功率谱   发端参考图，不受 SNR / Phase 影响
干净基带眼图     发端参考图，不受 SNR / Phase 影响
干净星座图       发端参考图，不受 SNR / Phase 影响
```

图表文字使用中文黑体优先：

```text
SimHei
Microsoft YaHei
```

## 默认参数

```text
TARGET_HOST = 127.0.0.1
TARGET_PORT = 9000
WEB_PORT = 8000
SNR_DB = 20.0
PHASE_DEG = 0.0
SAMPLES_PER_SYMBOL = 8
RRC_BETA = 0.35
RRC_SPAN = 8
UDP_FRAGMENT_PAYLOAD_BYTES = 1400
UDP_INTER_PACKET_DELAY_SEC = 0.0
```

页面中可以临时修改 UDP 目标 IP、端口、SNR 和 Phase。当前修改只保存在运行时，不写回 `config.py`。

## 重要边界

- UDP 发送的是 RRC 成型后、信道污染后的采样级数字基带 I/Q。
- UDP 不发送原图 bytes。
- UDP 不发送 bitstream。
- QPSK 和 QDPSK 必须每次同时执行、同时发包。
- 香橙派部署等 Receiver 开发和 PC 本机联调成功后再做。
# Current Implementation Notes - 2026-06-15

Current demo image boundary:

```text
source image: raw_pic_64.png
dimensions: 64x64
channels: RGB / 3
raw payload bytes: 12288
image frame bytes: 12297
```

The current end-to-end demo does not support arbitrary image dimensions. The Receiver fallback path also assumes `64x64x3` RGB when a noisy channel damages the `IMG0` header.

Current demo parameter limits:

```text
SNR:   6.0 .. 30.0 dB
Phase: -90 .. +90 deg
```

The UI, frontend JavaScript, and backend API all clamp to these ranges. For the phase-rotation demo, use high SNR (`25..30 dB`) and compare `0 deg`, `50 deg`, and `75 deg`: QPSK should fail as absolute phase crosses its decision boundaries, while QDPSK should remain recoverable for a common fixed phase rotation.
