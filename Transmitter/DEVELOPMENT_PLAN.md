# Transmitter 开发计划

## 定位

`Transmitter` 是项目里的下位机发射端工程。它先在 PC 上开发调试，之后应当能直接通过 SSH 传到香橙派运行。

它不是单纯的 UDP 发包脚本，也不使用 PySide / Qt 做桌面窗口。Transmitter 是一个 Python 主导的工程：DSP、通信图计算、图片生成、文件读取、UDP 发送和状态管理都在 Python 内完成。HTML 只作为 UI 描述层。

按照总蓝图，Transmitter 需要同时承担：

- 原图读取与信源编码
- QPSK / QDPSK 双通道并行调制
- RRC 基带成型
- 虚拟信道污染，也就是 AWGN 与相位旋转
- 双通道 UDP 封包与发送
- 下位机 HTML 控制界面，用来替代 Qt/PySide 类桌面 GUI。香橙派 Ubuntu 22.04 自带 Chromium，因此第一版直接用 Chromium 打开本地 HTML 服务
- 发端三张图表展示

发端三张图是第一版范围，不是后续可选项：

| 序号 | 图表名称 | 观测端 | 展示目的 |
| --- | --- | --- | --- |
| 1 | 发端基带眼图 (Eye Diagram) | 下位机 / 香橙派 | 展示基带信号经过 RRC 成型后的眼图，证明眼线清晰、ISI 可控 |
| 2 | 发端干净星座图 (Constellation) | 下位机 / 香橙派 | 展示调制后、信道污染前的标准 4 点星座 |
| 3 | 发端基带信号功率谱 (PSD) | 下位机 / 香橙派 | 展示 RRC 成型后的基带频谱主瓣与旁瓣 |

## 网络边界

必须把两条链路分清楚：

```text
链路 A：本机 UI 控制链路
Chromium/HTML  ->  本机 Python HTTP 接口  ->  调用 Python DSP / 画图 / 发 UDP

链路 B：真实通信数据链路
Transmitter Python  ->  UDP 双通道 IQ 帧  ->  Receiver Python
```

Flask 或其他轻量 HTTP 服务只属于链路 A，用来让 HTML 控件调用本机 Python。它不承担 TX/RX 之间的通信传输。

TX/RX 之间真正传输的是 UDP：

```text
AA BB 03 + qpsk_len + qdpsk_len + qpsk_iq_payload + qdpsk_iq_payload
```

开发和部署顺序必须是：

```text
阶段 1：同一台 PC 上跑 Transmitter 和 Receiver
        TX -> 127.0.0.1:9000 -> RX
        先确认协议、封包、拆包、算法联调成功

阶段 2：同一台 PC 上改成本机局域网 IP 测试
        TX -> PC_LAN_IP:9000 -> RX
        确认绑定地址、防火墙、端口没有问题

阶段 3：手机开热点，PC 和香橙派都连接热点
        OrangePi_TX -> PC_HOTSPOT_IP:9000 -> PC_RX
        Transmitter 迁移到香橙派后再部署
```

也就是说，香橙派部署不是第一步。先在 PC 上确认 RX/TX 联调成功，才把 Transmitter 目录复制到香橙派。

## 界面形态

第一版界面采用 HTML + CSS + 少量 JavaScript，由 Chromium 打开本地 Python HTTP 页面。

它的角色等价于传统 PySide / Qt 窗口：

```text
Chromium 浏览器窗口
 -> 本地 HTML 页面
 -> 文件预览
 -> 参数控件
 -> 发送按钮
 -> 加载 Python 生成的发端图 PNG
 -> 状态与统计显示
```

Python 是绝对主力，负责：

```text
读取图片文件
生成 QPSK / QDPSK 波形
计算眼图 / 星座图 / PSD
用 matplotlib Agg 生成 PNG 图像文件
封 UDP 包
发送 UDP
保存并返回当前配置
```

HTML 不是“宣传页”或“附加展示页”，而是 Transmitter 的主 GUI 外壳；JS 不承担 DSP，也不负责专业通信图计算。

### 是否使用 `pywebview`

第一版不使用。

原因：

- 香橙派 Ubuntu 22.04 已经自带 Chromium，不需要额外引入 pywebview 依赖。
- Chromium 对 HTML/CSS/JS 的兼容性更稳定，调试也更直接。
- 下位机接显示器时，可以用 Chromium 全屏或 kiosk 模式打开本地页面。
- Python 仍然是主力，Chromium 只是 UI 承载容器。
- 少一个 GUI 依赖，后续 SSH 迁移和环境恢复更简单。

建议模式：

```text
Python main.py
 -> 启动本地 Python HTTP 服务
 -> 用户或启动脚本打开 Chromium http://127.0.0.1:8000
 -> HTML 控件调用 Flask API
 -> Python 完成 DSP、画图、发 UDP
 -> HTML 刷新 Python 生成的 PNG 图片
```

后续如果想做得更像桌面 App，再考虑 pywebview，但它不是第一版必要项。

Chromium 可选启动方式：

```text
chromium-browser http://127.0.0.1:8000
chromium-browser --kiosk http://127.0.0.1:8000
```

## 第一版运行方式

不做复杂 CLI。

原因：

- 输入图片固定为 `raw_pic_64.png`。
- 下位机最终部署在香橙派，运行方式应尽量固定。
- 参数控制应该在 HTML 控件里完成，而不是依赖命令行。
- PC 调试和香橙派部署应使用同一套入口。

第一版使用：

```powershell
python main.py
```

启动后提供本机 HTML GUI：

```text
http://127.0.0.1:8000
```

PC 调试时直接用浏览器访问。迁移到香橙派后，接显示器打开 Chromium 访问同一地址。

```text
http://127.0.0.1:8000
```

## 主流程

```text
raw_pic_64.png
 -> 读取为 RGB 原始像素
 -> 添加图像元信息 header
 -> bytes 转 bitstream
 -> QPSK 绝对映射
 -> QDPSK 差分编码 + 映射
 -> 生成发端干净星座图数据
 -> RRC 基带成型
 -> 生成发端基带眼图数据
 -> 生成发端基带 PSD 数据
 -> 对两路成型波形施加相同 SNR / Phase Offset
 -> 双通道 UDP 封包
 -> 发送到 Receiver
```

## 推荐目录结构

```text
Transmitter/
  raw_pic_64.png
  DEVELOPMENT_PLAN.md
  config.py
  image_source.py
  bitstream.py
  modulation.py
  channel.py
  analysis.py
  plotter.py
  packet.py
  udp_sender.py
  web_app.py
  main.py
  templates/
    index.html
  static/
    app.js
    style.css
    generated/
      eye.png
      constellation.png
      psd.png
```

## 模块职责

### `config.py`

集中放置发射端默认参数。

```python
IMAGE_PATH = "raw_pic_64.png"

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 9000

WEB_HOST = "0.0.0.0"
WEB_PORT = 8000
AUTO_OPEN_BROWSER = False

SNR_DB = 20.0
PHASE_DEG = 0.0

SAMPLES_PER_SYMBOL = 8
RRC_BETA = 0.35
RRC_SPAN = 8

RANDOM_SEED = 20260615
```

### `image_source.py`

负责读取 `raw_pic_64.png`，并构造适合通信链路传输的图像字节。

不建议传 PNG 压缩字节。PNG 对误码极其敏感，少量 bit 错误可能导致整张图片无法解码；原始 RGB 即使有误码，也能直接显示花屏程度，更适合答辩时对比 QPSK 和 QDPSK。

建议图像数据格式：

```text
magic:     4 bytes, b"IMG0"
width:     uint16, big-endian
height:    uint16, big-endian
channels:  uint8, fixed 3
payload:   RGB raw bytes
```

### `bitstream.py`

负责 bytes 与 bitstream 转换。

```python
bytes_to_bits(data: bytes) -> np.ndarray
bits_to_bytes(bits: np.ndarray) -> bytes
```

### `modulation.py`

负责 QPSK / QDPSK 调制与 RRC 成型。

```python
qpsk_modulate(bits) -> np.ndarray
qdpsk_modulate(bits) -> np.ndarray
rrc_filter(beta, sps, span) -> np.ndarray
pulse_shape(symbols, rrc_taps, sps) -> np.ndarray
```

建议 Gray QPSK 映射固定为：

```text
00 ->  1 + 1j
01 -> -1 + 1j
11 -> -1 - 1j
10 ->  1 - 1j
```

所有星座点归一化到单位平均功率：

```text
symbol / sqrt(2)
```

QDPSK 流程：

```text
bits -> dibits -> phase_step in {0,1,2,3}
phase[k] = (phase_step[k] + phase[k-1]) mod 4
phase -> QPSK constellation symbol
```

Receiver 必须使用完全一致的映射表和差分规则。

### `channel.py`

负责虚拟信道污染。

```python
apply_phase_rotation(iq, phase_deg) -> np.ndarray
add_awgn(iq, snr_db, rng) -> np.ndarray
apply_channel(iq, snr_db, phase_deg, rng) -> np.ndarray
```

要求：

- QPSK 和 QDPSK 使用相同 `SNR_DB` 与 `PHASE_DEG`。
- 噪声功率计算规则一致。
- 固定随机种子，方便 PC 和香橙派调试结果复现。

### `analysis.py`

负责发端三张图所需的数值计算。

```python
compute_eye_traces(iq, sps, traces, span_symbols) -> np.ndarray
sample_constellation(symbols, max_points) -> np.ndarray
compute_psd(iq, sample_rate, nfft) -> tuple[np.ndarray, np.ndarray]
```

数据来源必须明确：

- 眼图数值：RRC 成型后的干净基带波形，不使用加噪/旋转后的波形。
- 星座图数值：调制后的干净符号点，不使用信道污染后的波形。
- PSD 数值：RRC 成型后的干净基带波形。

第一版页面至少展示一组发端图。建议默认展示 QDPSK，并提供 QPSK / QDPSK 切换。

### `plotter.py`

负责用 Python 生成发端三张图的 PNG 文件。

```python
render_eye_png(eye_traces, output_path) -> None
render_constellation_png(symbols, output_path) -> None
render_psd_png(freqs, psd_db, output_path) -> None
render_all_tx_plots(tx_result, output_dir) -> dict
```

要求：

- 使用 matplotlib Agg 后端生成专业 PNG，避免依赖桌面显示后端。
- 保留轻量纯 Python PNG 渲染器作为 fallback。
- 输出文件放在 `static/generated/`。
- HTML 只通过 `<img>` 加载 PNG。
- 图标题、坐标轴、网格、单位由 Python 控制。
- JS 不计算眼图、星座图或 PSD。

### `packet.py`

负责 UDP 应用层帧封包。

UDP 传输的不是比特流，也不是原图本体，而是**采样后的数字基带 I/Q 数据**。

第一版建议默认使用 `complex64`，也就是每个采样点两个 float32：

```python
np.asarray(iq, dtype=np.complex64).tobytes()
```

协议格式：

```text
+------------------+------------------+-----------------------+-----------------------+-----------------------------+
| Header 2 bytes    | Mode 1 byte      | QPSK length 4 bytes   | QDPSK length 4 bytes  | Payload                     |
| 0xAA 0xBB         | 0x03             | uint32 big-endian     | uint32 big-endian     | QPSK IQ + QDPSK IQ          |
+------------------+------------------+-----------------------+-----------------------+-----------------------------+
```

后续如果需要压缩带宽，可以再考虑 `int16` I/Q 打包，但那是第二阶段优化，不是第一版默认值。

### `udp_sender.py`

负责 UDP 发送。

```python
send_packet(packet: bytes, host: str, port: int) -> None
```

UDP 是无连接发送，没有 Receiver 时也不应报连接错误。

### `web_app.py`

负责把 Python 后端能力暴露给 HTML GUI，并提供 Python 生成的图像文件。

建议使用 Flask，部署到香橙派简单，依赖少，调试直观。

第一版接口：

```text
GET  /                 下位机控制页
GET  /api/state        当前配置、图片尺寸、链路统计
GET  /api/tx-plots     发端眼图、干净星座图、PSD 的 PNG 路径和版本号
POST /api/config       更新 SNR_DB / PHASE_DEG
POST /api/send         按当前参数生成波形并 UDP 发送一次
POST /api/render       重新计算 DSP 并生成发端三图 PNG
```

### `templates/index.html`

正式 GUI 页面，替代 PySide / Qt 窗口。

页面第一版功能：

```text
显示原始 64x64 图片
显示 SNR 滑块
显示 Phase Offset 滑块
显示发送按钮
通过 img 显示 Python 生成的发端基带眼图 PNG
通过 img 显示 Python 生成的发端干净星座图 PNG
通过 img 显示 Python 生成的发端基带 PSD PNG
显示最近一次发送统计
```

建议布局：

```text
+----------------------------------------------------------+
| 顶部状态栏：目标地址、端口、当前 SNR、Phase、发送状态      |
+----------------------+-----------------------------------+
| 原始图片预览          | 参数控件                          |
| raw_pic_64.png        | SNR slider                         |
|                      | Phase slider                       |
|                      | Send button                        |
+----------------------+-----------------------------------+
| 发端基带眼图 PNG                                         |
+----------------------------------------------------------+
| 发端干净星座图 PNG          | 发端基带 PSD PNG                 |
+----------------------------------------------------------+
| 最近一次发送统计                                             |
+----------------------------------------------------------+
```

### `static/app.js`

负责 HTML 控件与 Python 后端接口对接。

第一版职责：

```text
页面加载时请求 /api/state
页面加载时请求 /api/tx-plots
滑块改变时 POST /api/config
点击发送时 POST /api/send
必要时 POST /api/render 触发 Python 重新生成 PNG
刷新 img src，加载 Python 生成的眼图、星座图、PSD
刷新发送统计
```

第一版不需要复杂前端框架，原生 JavaScript 足够。JS 只做 UI 事件、接口调用和图片刷新。

### `static/style.css`

负责界面排版与控件样式。

原则：

```text
像仪表盘，不像宣传页
信息密度高
控件位置稳定
图表区域尺寸固定
适配 PC 浏览器和香橙派局域网访问
```

图表第一版由 Python/matplotlib 生成 PNG，HTML 只加载图片。这样更严谨，也能保证通信图的所有计算和绘制都留在 Python 体系内。

### `main.py`

发射端入口。

```text
加载 config.py
初始化图片信源
启动 Flask 后端
可选自动打开 Chromium
由 HTML 控件触发参数更新、Python 画图和 UDP 发送
```

启动时打印：

```text
image path
image size
target host / port
default SNR / phase
web server URL
browser open status
```

每次发送后记录：

```text
image bytes
bit count
QPSK symbol count
QDPSK symbol count
QPSK sample count
QDPSK sample count
UDP packet bytes
SNR / phase
send timestamp
```

## 分轮开发计划

不要一步登天。Transmitter 按轮次推进，每一轮都要有可运行、可验收的结果。

### 第 1 轮：工程骨架与图片信源

目标：确认 Python 工程能稳定读取原图，并把图像变成可传输 bitstream。

完成：

- 建立基础文件结构
- 写 `config.py`
- 读取 `raw_pic_64.png`
- 转为 RGB
- 生成自定义图像数据帧
- bytes 转 bitstream
- 输出长度统计

涉及文件：

```text
config.py
image_source.py
bitstream.py
main.py
```

验收：

- `python main.py` 可运行
- 图片尺寸为 `64x64`
- 原始 RGB payload 长度为 `64 * 64 * 3 = 12288` bytes
- 加 header 后 bitstream 长度稳定可复现
- 终端打印 image bytes、bit count

本轮不做：调制、RRC、画图、UDP、HTML。

### 第 2 轮：QPSK / QDPSK 符号映射

目标：把核心双通道调制规则定死，保证 Receiver 将来能按同一规则反解。

完成：

- QPSK Gray 映射
- QDPSK 差分编码
- 星座点单位功率归一化

涉及文件：

```text
modulation.py
main.py
```

验收：

- 输入 bit 数为偶数
- 两路 symbol 数一致
- symbol 平均功率接近 1
- 干净星座点只有 4 个理想聚类
- 终端打印 QPSK/QDPSK symbol count 和平均功率

本轮不做：信道污染、UDP、HTML。

### 第 3 轮：RRC 成型与基础波形

目标：完成发端基带成型，让后续眼图和 PSD 有真实数据来源。

完成：

- RRC taps 生成
- 上采样
- 卷积成型
- 计算 filter delay 和采样点数量

涉及文件：

```text
modulation.py
main.py
```

验收：

- 输出采样点数符合预期
- 无 NaN / Inf
- 平均功率合理
- 终端打印 QPSK/QDPSK sample count

本轮不做：图像渲染、UDP、HTML。

### 第 4 轮：Python 发端三图 PNG

目标：把蓝图要求的下位机三张图用 Python 画出来，先落成 PNG 文件。

完成：

- 发端基带眼图数值计算
- 发端干净星座图数值计算
- 发端基带 PSD 数值计算
- matplotlib Agg 生成三张 PNG

涉及文件：

```text
analysis.py
plotter.py
main.py
static/generated/
```

验收：

- 眼图来自 RRC 成型后的干净基带波形
- 星座图来自调制后的干净符号
- PSD 来自 RRC 成型后的干净基带波形
- `static/generated/eye.png` 存在
- `static/generated/constellation.png` 存在
- `static/generated/psd.png` 存在
- 人眼打开 PNG 能看出图形合理

本轮不做：HTML、UDP、动态滑块。

### 第 5 轮：AWGN 与相位旋转

目标：完成发射端虚拟信道污染，保证两路使用同一组信道参数。

完成：

- 固定相位旋转
- 按 SNR 添加复高斯白噪声
- 对 QPSK/QDPSK 两路使用相同 SNR 与 phase

涉及文件：

```text
channel.py
main.py
```

验收：

- `PHASE_DEG = 0` 时不改变相位
- `SNR_DB` 越低，噪声越明显
- 同一随机种子下输出可复现
- 终端打印污染后两路平均功率

本轮不做：Receiver 解调、HTML 控制。

### 第 6 轮：UDP 封包与发送

目标：把双通道污染后 IQ 按项目协议封装并发送。

注意：如果发送的是 RRC 成型后的采样级 `complex64` IQ，单帧可能达到数 MB，不能塞进单个 UDP 包。第 6 轮开始前必须先确定传输策略：

```text
方案 A：发送采样级 IQ，必须做 UDP 分片、序号、总片数和重组。
方案 B：发送符号级数据或较低速数据，由 Receiver 端重建成型波形。
```

当前推荐方案 A，但默认承载格式仍然是 `complex64`。如果后面带宽或传输效率不够，再把同一套分片协议切到 `int16` I/Q。

完成：

- 两路 IQ 转 `complex64` bytes
- 按协议封包
- UDP 发送到 `TARGET_HOST:TARGET_PORT`

涉及文件：

```text
packet.py
udp_sender.py
main.py
```

验收：

- packet header 为 `AA BB 03`
- QPSK / QDPSK 长度字段与 payload 实际长度一致
- 没有 Receiver 时运行也不报错
- 终端打印 UDP packet bytes 和目标地址

本轮不做：接收端联调、高频循环发送。

### 第 7 轮：HTML GUI 静态页面

目标：先把界面框架搭起来，用 Chromium 打开页面能看到原图、三张 Python PNG 和基础状态。

完成：

- Flask 服务
- `templates/index.html`
- `static/app.js`
- `static/style.css`
- 原图预览控件
- 三张发端图 PNG 显示区
- 只读状态面板

涉及文件：

```text
web_app.py
templates/index.html
static/app.js
static/style.css
main.py
```

验收：

- PC 上运行 `python main.py` 后访问 `http://127.0.0.1:8000` 能操作
- 香橙派接显示器后用 Chromium 打开 `http://127.0.0.1:8000` 能操作
- 页面能显示原图
- 页面能显示 Python 生成的三张 PNG
- 页面能显示当前配置和统计信息

本轮不做：滑块更新参数、按钮发送、自动刷新。

### 第 8 轮：HTML 控件接入 Python 后端

目标：让 HTML 真正成为操作面板，但计算和画图仍然全部在 Python。

完成：

- SNR 滑块控件
- Phase Offset 滑块控件
- 发送按钮控件
- `POST /api/config`
- `POST /api/render`
- `POST /api/send`
- 最近一次发送统计面板

涉及文件：

```text
web_app.py
static/app.js
templates/index.html
```

验收：

- 页面修改参数后，发包使用最新 SNR / Phase
- 点击重新生成后，Python 更新三张 PNG，HTML 刷新图片
- 点击发送后，Python 重新生成两路 IQ、封包并 UDP 发送
- 不依赖 PySide / Qt
- HTML 页面是 Transmitter 的主操作界面，但 DSP 和图表生成全部由 Python 完成

本轮不做：高频 `oninput` 连续发送、Receiver 联调。

### 第 9 轮：PC 本机 RX/TX 联调

目标：在同一台 PC 上先确认 Transmitter 与 Receiver 联调成功。只有这一轮通过后，才允许迁移到香橙派。

完成：

- Receiver 启动 UDP 监听 `127.0.0.1:9000`
- Transmitter 目标地址设置为 `127.0.0.1:9000`
- 点击 HTML 发送按钮触发 UDP 发包
- Receiver 能解析包头、长度字段和两路 complex64 payload
- Receiver 至少能打印 QPSK/QDPSK 样本数和基础功率统计

验收：

- `AA BB 03` 解析正确
- QPSK / QDPSK payload 长度正确
- Receiver 反序列化后的 complex64 数组长度正确
- 多次点击发送，Receiver 都能稳定收到
- 修改 SNR / Phase 后重新发送，Receiver 侧统计有变化

本轮不做：香橙派部署、热点局域网部署、高频连续发送。

### 第 10 轮：香橙派迁移与热点局域网部署

目标：PC 本机 RX/TX 联调成功后，把 Transmitter 迁移到香橙派，并通过手机热点局域网向 PC Receiver 发送。

完成：

- 补 `requirements.txt`
- 补运行说明
- 检查相对路径
- 检查 Python PNG 图表生成路径
- 检查 Chromium 打开方式
- PC 和香橙派连接同一个手机热点
- PC Receiver 绑定热点局域网 IP 和端口
- 香橙派 Transmitter 的 `TARGET_HOST` 指向 PC 热点局域网 IP
- 香橙派 Chromium 打开 `http://127.0.0.1:8000`
- 通过香橙派页面点击发送

验收：

- PC Receiver 能收到香橙派发来的 UDP 包
- Receiver 能解析 `AA BB 03` 双通道包
- 修改 SNR / Phase 后重新发送，Receiver 能看到对应变化
- 香橙派接显示器能稳定显示 HTML GUI、原图和三张发端图
- 可选使用 Chromium kiosk 模式全屏展示

后续增强：

- 连续发送
- 滑块释放后自动重新发送
- `oninput` 高频打流
- Chromium kiosk 启动脚本

## 第一版完成标准

运行：

```powershell
python main.py
```

能够完成：

- 启动下位机 HTML GUI，由 Chromium 承载
- 读取并显示 `raw_pic_64.png`
- 显示 Python 生成的发端基带眼图
- 显示 Python 生成的发端干净星座图
- 显示 Python 生成的发端基带 PSD
- 通过页面调整 SNR 和 Phase Offset
- 通过页面触发一次 UDP 发送
- 生成 QPSK 和 QDPSK 两路受损 IQ
- 按统一协议封包并发送到 Receiver 地址
- 页面显示完整链路统计信息

第一版不做：

- Receiver 解调
- Gardner 同步
- 群同步
- 接收端图表
- PDF 报告
- 自动循环高频打流

自动循环和 `oninput` 高频触发可以作为第二版增强，等第一版单次发送和三图展示稳定后再加。
# Current Implementation Override - 2026-06-15

This section overrides older protocol text in this planning document.

Current UDP transport is fragmented per channel. It is not the older single-packet layout `AA BB 03 + qpsk_len + qdpsk_len + payload`.

Current datagram layout:

```text
26-byte application header + complex64 IQ payload
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

Current default frame:

```text
source image: raw_pic_64.png
image: 64x64 RGB
samples per channel: 393568 complex64
chunks per channel: 2249
total UDP packets: 4498
```

Current demo parameter limits:

```text
SNR:   6.0 .. 30.0 dB
Phase: -30 .. +30 deg
```

Receiver status:

- PC-local TX/RX integration is complete through UDP reassembly.
- Receiver saves complete QPSK/QDPSK `.npy` captures.
- Receiver offline analyzer recovers QPSK/QDPSK PNGs and prints MSE/PSNR.
- Receiver degraded-image fallback assumes fixed `64x64x3` RGB.

Arbitrary image dimensions are not supported yet.
