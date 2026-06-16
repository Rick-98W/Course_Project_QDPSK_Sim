# Transmitter 交接文档

本文档用于新会话无上下文接手开发。先阅读本文，再继续改代码。

## 项目定位

`Transmitter` 是 QDPSK 课程设计项目中的下位机发射端工程。

目标不是发送原图、不是发送 bitstream，而是完整模拟数字通信发射链路：

```text
64x64 原图
 -> RGB bytes
 -> bitstream
 -> QPSK / QDPSK 双通道调制
 -> RRC 基带成型
 -> 数学信道污染：AWGN + Phase Rotation
 -> 采样后的数字基带 I/Q
 -> UDP 分片发送给 Receiver
```

Receiver 后续需要接收 UDP 分片、重组 I/Q、同步、解调、解码并恢复图像。

重要边界：

- UDP 传的是**采样后的数字基带 I/Q**。
- UDP 不传原图 bytes。
- UDP 不传 bitstream。
- 手机热点只是局域网承载，不负责产生 AWGN 或相位旋转。
- AWGN / phase rotation 在 Python 发射端脚本里模拟。

## 环境

指定 conda 环境：

```powershell
conda activate QDRSK_TX_ELB
```

解释器：

```text
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe
```

已确认：

```text
Python 3.10.20
NumPy 2.2.6
Matplotlib 3.10.9
```

如果 `numpy.linalg.inv(np.eye(2))` 或 matplotlib 保存图时崩溃，原因可能是 BLAS/LAPACK 后端问题。已用 OpenBLAS 修过：

```powershell
conda install -c conda-forge "libblas=*=*openblas" "liblapack=*=*openblas" --update-deps --force-reinstall numpy matplotlib
```

修复验证：

```powershell
python -c "import numpy as np; print(np.__version__); print(np.linalg.inv(np.eye(2)))"
python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.plot([1,2,3]); plt.savefig('mpl_test.png'); print('ok')"
```

## 当前文件

```text
Transmitter/
  raw_pic_64.png
  README.md
  RECEIVER_INTERFACE.md
  DEVELOPMENT_PLAN.md
  DEVELOPMENT_LOG.md
  HANDOFF.md
  config.py
  image_source.py
  bitstream.py
  modulation.py
  analysis.py
  plotter.py
  plotter_fallback.py
  channel.py
  packet.py
  preview_dump.py
  udp_sender.py
  tx_pipeline.py
  web_app.py
  main.py
  templates/
    index.html
  static/
    app.js
    style.css
  static/
    generated/
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
      qpsk_packet_preview.txt
      qdpsk_packet_preview.txt
```

## 已完成轮次

### 第 1 轮：图片信源

文件：

```text
config.py
image_source.py
bitstream.py
main.py
```

实现：

- 读取 `raw_pic_64.png`
- 标准库解析 PNG 为 RGB bytes
- 构造图像通信帧
- bytes 转 bitstream

图像帧格式：

```text
magic:     4 bytes, b"IMG0"
width:     uint16, big-endian
height:    uint16, big-endian
channels:  uint8, fixed 3
payload:   RGB raw bytes
```

关键结果：

```text
raw RGB payload bytes: 12288
image frame bytes: 12297
bit count: 98376
roundtrip bytes match: True
```

### 第 2 轮：QPSK / QDPSK 符号映射

文件：

```text
modulation.py
```

QPSK Gray 映射：

```text
00 ->  1 + 1j
01 -> -1 + 1j
11 -> -1 - 1j
10 ->  1 - 1j
```

归一化：

```text
symbol / sqrt(2)
```

QDPSK：

```text
bits -> dibits -> phase_step in {0,1,2,3}
phase[k] = (phase_step[k] + phase[k-1]) mod 4
phase -> QPSK constellation symbol
```

关键结果：

```text
QPSK symbol count: 49188
QDPSK symbol count: 49188
QPSK average power: 1.000000
QDPSK average power: 1.000000
```

### 第 3 轮：RRC 成型

文件：

```text
modulation.py
```

当前参数：

```text
SAMPLES_PER_SYMBOL = 8
RRC_BETA = 0.35
RRC_SPAN = 8
```

关键结果：

```text
RRC tap count: 65
RRC tap energy: 1.000000
RRC filter delay samples: 32
QPSK waveform sample count: 393568
QDPSK waveform sample count: 393568
QPSK waveform average power: 0.125173
QDPSK waveform average power: 0.125092
```

### 第 4 轮：发端三图

文件：

```text
analysis.py
plotter.py
plotter_fallback.py
```

生成：

```text
static/generated/qpsk_psd.png
static/generated/qdpsk_psd.png
static/generated/qpsk_eye.png
static/generated/qdpsk_eye.png
static/generated/qpsk_constellation.png
static/generated/qdpsk_constellation.png
```

当前 `plotter.py` 使用 matplotlib Agg。`plotter_fallback.py` 是不用 matplotlib 的备用 PNG 渲染器。

注意：

- QPSK 和 QDPSK 每次同时生成，不再二选一。
- 发端眼图来自干净 RRC 成型波形。
- 发端干净星座图来自调制后、信道前的符号，所以只有 4 个点是正确的。
- 发端 PSD 来自干净 RRC 成型波形。
- 这些图不使用信道污染后的数据。
- 信道后星座图来自 `apply_channel(SNR, Phase)` 之后的受损采样 IQ，会随 SNR / Phase 改变。
- 信道后眼图来自 `apply_channel(SNR, Phase)` 之后的受损 IQ，会随 SNR / Phase 改变。

### 第 5 轮：AWGN 与相位旋转

文件：

```text
channel.py
```

当前参数：

```text
SNR_DB = 20.0
PHASE_DEG = 0.0
RANDOM_SEED = 20260615
```

实现：

- 固定相位旋转
- 复高斯白噪声
- 信道统计

关键结果：

```text
QPSK impaired power: 0.126467
QDPSK impaired power: 0.126341
QPSK estimated SNR dB: 20.012
QDPSK estimated SNR dB: 19.999
```

### 第 6 轮：UDP 分片发送

文件：

```text
packet.py
udp_sender.py
preview_dump.py
main.py
```

当前传输内容：

```text
采样后的数字基带 I/Q
格式：complex64
```

不是：

```text
原图 bytes
bitstream
符号索引
```

当前分片参数：

```text
UDP_FRAGMENT_PAYLOAD_BYTES = 1400
UDP_INTER_PACKET_DELAY_SEC = 0.0
```

单帧结果：

```text
QPSK packet count: 2249
QDPSK packet count: 2249
QPSK first packet bytes: 1426
QDPSK first packet bytes: 1426
UDP packets sent: 4498
UDP total bytes: 6414036
```

预览文件：

```text
static/generated/qpsk_packet_preview.txt
static/generated/qdpsk_packet_preview.txt
```

预览文件里可以看到：

```text
magic=b'\xaa\xbb'
mode=3
version=1
frame_id=...
channel_id=0 或 1
sample_format=1
chunk_index=0/2249
start_sample=0
chunk_samples=175
total_samples=393568
payload_bytes=1400
first_samples=[复数 IQ 采样值...]
payload_hex=...
```

`channel_id`：

```text
0 = QPSK
1 = QDPSK
```

`sample_format`：

```text
1 = complex64
```

### 第 7-9 轮：HTML GUI 与双通道并列展示

文件：

```text
tx_pipeline.py
web_app.py
main.py
templates/index.html
static/app.js
static/style.css
```

当前运行方式：

```powershell
conda activate QDRSK_TX_ELB
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
python main.py
```

然后浏览器访问：

```text
http://127.0.0.1:8000
```

注意：

- 不要直接双击 `templates/index.html` 使用；HTML 需要 Python HTTP 服务提供 API 和图片路径。
- 如果希望在 PyCharm Terminal 看到后端打印，必须在 PyCharm Terminal 里直接运行 `python main.py`；后台进程的输出不会显示在那里。
- 当前没有安装 Flask，`web_app.py` 使用 Python 标准库 `http.server`。
- Chromium/浏览器只是 GUI 外壳，DSP、画图、封包和 UDP 发送都在 Python 里执行。
- Python/matplotlib 生成的 PNG 图表统一使用黑体优先（`SimHei` / `Microsoft YaHei`）。
- SNR / Phase 控件通过 `/api/config` 同步到 Python。
- UDP 目标 IP / 端口可在页面运行时修改，默认仍是 `127.0.0.1:9000`。
- Render 按钮通过 `/api/render` 同时重新生成 QPSK/QDPSK 两套图。
- Send UDP 按钮通过 `/api/send` 同时生成两路受损 IQ、分片并发送。
- Python terminal 会打印 `[CONFIG]`、`[RENDER]`、`[SEND]` 和每次操作摘要。
- SNR / Phase 只影响信道污染后的 IQ 和 UDP 发送统计，不影响页面展示的发端 PSD、眼图、干净星座图。
- SNR / Phase 会影响页面展示的信道后星座图。
- 页面图像 URL 使用 PNG 文件纳秒级 mtime 作为版本号，Render / Send 后浏览器会重新请求图片。

当前 HTML 图表布局：

```text
           QPSK                              QDPSK
信道后星座 qpsk_impaired_constellation.png   qdpsk_impaired_constellation.png
信道后眼图 qpsk_impaired_eye.png             qdpsk_impaired_eye.png
干净 PSD   qpsk_psd.png                      qdpsk_psd.png
干净眼图   qpsk_eye.png                      qdpsk_eye.png
干净星座   qpsk_constellation.png            qdpsk_constellation.png
```

## 运行测试

在 PowerShell 中运行：

```powershell
conda activate QDRSK_TX_ELB
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
python main.py
```

关键输出应包含：

```text
Transmitter round 8: dual-channel HTML control page
QPSK symbol count: 49188
QDPSK symbol count: 49188
RRC tap energy: 1.000000
QPSK waveform sample count: 393568
QDPSK waveform sample count: 393568
SNR target dB: 20.000
QPSK estimated SNR dB: 20.012
QPSK packet count: 2249
QDPSK packet count: 2249
web server URL: http://127.0.0.1:8000
```

然后查看：

```text
static/generated/qpsk_psd.png
static/generated/qdpsk_psd.png
static/generated/qpsk_eye.png
static/generated/qdpsk_eye.png
static/generated/qpsk_constellation.png
static/generated/qdpsk_constellation.png
static/generated/qpsk_impaired_constellation.png
static/generated/qdpsk_impaired_constellation.png
static/generated/qpsk_impaired_eye.png
static/generated/qdpsk_impaired_eye.png
static/generated/qpsk_packet_preview.txt
static/generated/qdpsk_packet_preview.txt
```

## 当前重要设计决策

### RGB vs 灰度

第一版保留 RGB。

理由：

- 64x64 RGB 体量可接受。
- 展示效果明显。
- QPSK 花屏 / QDPSK 稳定的对比更有说服力。

灰度可以作为后续调试加速模式，但不是默认。

### complex64 vs int16

第一版使用 `complex64`。

理由：

- 保持浮点精度。
- 方便调试 Receiver。
- 不先引入量化误差。
- 64x64 RGB 单帧传输量可接受。

`int16` I/Q 可以作为后续压缩优化。它会有量化损失，但如果按峰值或 RMS 做合理缩放，损失通常可控。不要在链路未闭环前引入这个变量。

### UDP 发送速度

`UDP_INTER_PACKET_DELAY_SEC` 当前是 `0.0`。

之前试过 `0.0005`，但 Windows `time.sleep` 计时粒度导致发送耗时接近 70 秒。先不要加包间隔。

后续如果做连续发送或滑块高频触发，再单独设计节流。

## 下一步建议

当前 Transmitter 在移植香橙派前的收尾工作已经完成。

下一阶段建议切到 Receiver 开发。Receiver 开发时优先阅读：

```text
RECEIVER_INTERFACE.md
```

建议 Receiver 开发顺序：

```text
1. 最小 UDP listener，绑定 127.0.0.1:9000
2. 解析 26-byte application header
3. 按 (frame_id, channel_id) 收集分片
4. 分别重组 QPSK / QDPSK complex64 IQ
5. 校验每路 chunk_count=2249、total_samples=393568
6. 打印 dtype、sample count、average power
7. 再继续同步、解调、差分解码和图像恢复
```

香橙派部署仍然放在 Receiver 完成且 PC 本机 TX/RX 联调通过之后。

## 接手注意事项

- 不要把 UDP 改成发送 bitstream。
- 不要把 UDP 改成发送原图 bytes。
- QPSK 和 QDPSK 必须每次同时执行、同时生成图、同时发包，不要做成二选一。
- Receiver 对接必须参考 `RECEIVER_INTERFACE.md`。
- 发端六张图必须来自干净发端信号。
- 信道后星座图必须来自受损采样 IQ，用来体现噪声和相位旋转。
- 信道后眼图必须来自受损 IQ，用来体现噪声导致眼图闭合。
- 图表文字当前统一为中文黑体；如果香橙派缺字体，需要安装字体或设置 fallback。
- 信道污染后的 IQ 才进入 UDP。
- Receiver 后续必须对 `complex64` IQ 做同步、解调、解码。
- 手机热点部署前，必须先在同一台 PC 上完成 TX/RX 联调。
- `DEVELOPMENT_LOG.md` 记录了每轮历史。
- `DEVELOPMENT_PLAN.md` 是总体路线图，但当前用户要求本阶段只推进 Transmitter。
# Current Handoff Update - 2026-06-15

Receiver is no longer only a future integration target. Current PC-local integration status:

- Receiver listens on `127.0.0.1:9000`.
- Receiver parses the current 26-byte fragmented UDP header.
- Receiver reassembles QPSK and QDPSK `complex64` IQ streams.
- Receiver saves captures under `Receiver/captures/frame_*/qpsk.npy` and `qdpsk.npy`.
- Receiver offline analyzer performs matched filtering, fixed timing sampling, QPSK/QDPSK demodulation, image recovery, PNG output, and MSE/PSNR comparison.
- Recovered files are `qpsk_recovered.png` and `qdpsk_recovered.png`.
- Degraded-channel fallback assumes fixed `64x64x3` RGB when the `IMG0` header is damaged.

Current Transmitter demo constraints:

```text
source image: raw_pic_64.png
image dimensions: 64x64 RGB
SNR:   6.0 .. 30.0 dB
Phase: -90 .. +90 deg
```

The current demo does not support arbitrary image dimensions. Keep the current fragmented `complex64` IQ protocol; do not return to the older single-packet length-field protocol.
