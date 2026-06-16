# Transmitter 开发日志

## 环境约定

后续 Transmitter 开发指定使用 conda 环境：

```text
QDRSK_TX_ELB
```

解释器路径：

```text
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe
```

当前确认版本：

```text
Python 3.10.20
NumPy 2.2.6
Matplotlib 3.10.9
```

注意：直接在普通 PowerShell 中运行 `python` 可能会命中其他解释器。开发和测试时应先激活 conda 环境，或显式使用上面的解释器路径。

### 2026-06-15 环境修复记录

问题：

```text
numpy.linalg.inv(np.eye(2)) 触发 Windows fatal exception 0xc06d007f
matplotlib 保存图时也会因为内部调用 numpy.linalg 而崩溃
```

根因判断：

```text
QDRSK_TX_ELB 环境原先使用 conda-forge MKL 2026.0.0 相关 BLAS/LAPACK，
当前 Windows 环境下 NumPy 线性代数后端异常。
```

修复命令：

```powershell
conda activate QDRSK_TX_ELB
conda install -c conda-forge "libblas=*=*openblas" "liblapack=*=*openblas" --update-deps --force-reinstall numpy matplotlib
```

修复后验证：

```powershell
python -c "import numpy as np; print(np.__version__); print(np.linalg.inv(np.eye(2)))"
python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.plot([1,2,3]); plt.savefig('mpl_test.png'); print('ok')"
```

结果：

```text
NumPy linalg 正常
Matplotlib Agg 保存 PNG 正常
```

## 第 1 轮：工程骨架与图片信源

状态：已完成。

完成内容：

- 新增 `config.py`
- 新增 `image_source.py`
- 新增 `bitstream.py`
- 新增 `main.py`
- 读取 `raw_pic_64.png`
- 解析 PNG 为原始 RGB 字节
- 构造图像通信帧
- 将 bytes 转为 bitstream
- 将 bitstream roundtrip 回 bytes 并校验一致性

当前图像通信帧格式：

```text
magic:     4 bytes, b"IMG0"
width:     uint16, big-endian
height:    uint16, big-endian
channels:  uint8, fixed 3
payload:   RGB raw bytes
```

验证结果：

```text
image size: 64x64
image channels: 3
raw RGB payload bytes: 12288
image frame bytes: 12297
bit count: 98376
frame magic: b'IMG0'
roundtrip bytes match: True
```

说明：

- 第一轮暂未引入 Pillow。
- 当前 `image_source.py` 使用标准库解析本项目自带 PNG，避免第一轮卡在依赖安装上。
- 后续如果要支持任意图片格式，再把 Pillow 加入依赖。

## 第 2 轮：QPSK / QDPSK 符号映射

状态：已完成。

完成内容：

- 新增 `modulation.py`
- 实现 `bits_to_dibits`
- 实现 QPSK Gray 映射
- 实现 QDPSK 差分编码
- 实现 QDPSK 调制
- 在 `main.py` 中打印两路符号数量、平均功率和唯一星座点

固定 Gray QPSK 映射：

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

验证结果：

```text
QPSK symbol count: 49188
QDPSK symbol count: 49188
QPSK average power: 1.000000
QDPSK average power: 1.000000
QPSK unique constellation points: 4 ideal points
QDPSK unique constellation points: 4 ideal points
```

## 带宽与实时性判断

64x64 原始 RGB 图片本身不大：

```text
64 * 64 * 3 = 12288 bytes
```

当前图像帧加 header 后：

```text
12297 bytes
```

调制后符号数：

```text
49188 symbols per channel
```

真正的带宽风险不在图片，而在后续如果发送 RRC 成型后的全采样 IQ。

例如 `SAMPLES_PER_SYMBOL = 8` 时，单路采样点大约是：

```text
49188 * 8 ~= 393504 complex samples
```

如果使用 `complex64`，单路大约：

```text
393504 * 8 ~= 3.1 MB
```

双路大约：

```text
6.3 MB per image frame
```

结论：

- PC Receiver 用 NumPy 处理这个数据量问题不大。
- 手机热点带宽传单次或低频发送通常够。
- 高频连续打流会吃紧。
- 单个 UDP 包肯定装不下这种采样级 IQ，需要分片。
- 第 6 轮前必须确定最终传输策略：发送采样级 IQ 并做 UDP 分片，或发送符号级数据让 Receiver 端重建成型波形。

当前结论：

- 第一版发送的是**采样后的数字基带 I/Q**，不是比特流。
- 默认承载格式先用 `complex64`，方便保持浮点精度和调试直观性。
- `int16` 可以作为后续带宽优化选项，但不是第一版默认方案。
- 64x64 RGB 做课程设计展示足够，不必先降到灰度图；灰度只适合作为调试加速模式。

## 第 3 轮：RRC 成型与基础波形

状态：已完成。

完成内容：

- 在 `modulation.py` 中新增 `rrc_filter`
- 新增 `upsample_symbols`
- 新增 `pulse_shape`
- 新增 `filter_delay_samples`
- `main.py` 输出 RRC 参数、tap 数量、filter delay、两路波形采样点数和平均功率

当前 RRC 参数：

```text
RRC_BETA = 0.35
RRC_SPAN = 8 symbols
SAMPLES_PER_SYMBOL = 8
```

验证结果：

```text
RRC tap count: 65
RRC tap energy: 1.000000
RRC filter delay samples: 32
QPSK waveform sample count: 393568
QDPSK waveform sample count: 393568
QPSK waveform average power: 0.125173
QDPSK waveform average power: 0.125092
```

说明：

- `65 = RRC_SPAN * SAMPLES_PER_SYMBOL + 1`。
- `393568 = 49188 * 8 + 65 - 1`，因为当前使用 full convolution 保留滤波器瞬态。
- 波形平均功率约等于 `1 / SAMPLES_PER_SYMBOL` 是合理的；单位能量滤波器加插零上采样后，采样级平均功率会低于符号功率。

## 第 6 轮：UDP 封包与发送

状态：已完成。

完成内容：

- 新增 `packet.py`
- 新增 `udp_sender.py`
- 采用采样级 `complex64` IQ 作为 UDP 传输内容
- 对 QPSK / QDPSK 两路污染后波形分别分片
- 每片控制在接近 MTU 的安全范围内
- 在 `main.py` 中发送双通道分片包

当前传输口径：

```text
UDP 传的是采样后的数字基带 I/Q，不是比特流，也不是原图 bytes。
默认承载格式是 complex64。
```

分片参数：

```text
UDP_FRAGMENT_PAYLOAD_BYTES = 1400
```

验证结果：

```text
QPSK packet count: 2249
QDPSK packet count: 2249
QPSK first packet bytes: 1426
QDPSK first packet bytes: 1426
UDP packets sent: 4498
UDP total bytes: 6414036
UDP elapsed sec: 0.026
```

说明：

- 第一次实验把包间隔设成 `0.0005` 秒，但 Windows 计时粒度导致发送耗时接近 70 秒。
- 现在默认 `UDP_INTER_PACKET_DELAY_SEC = 0.0`，先保证一帧图像能快速发完。
- 后续如果要做连续打流或滑块实时触发，再单独加节流和批次控制。
- 如果后面带宽或 CPU 压力大，再考虑把同一套分片协议切到 `int16` I/Q。

## 第 7 轮计划

第 7 轮：HTML GUI 静态页面。

目标：

- 先把界面框架搭起来，用 Chromium 打开页面能看到原图、三张 Python PNG 和基础状态

## 第 4 轮：Python 发端三图 PNG

状态：已完成。

完成内容：

- 新增 `analysis.py`
- 新增 `plotter.py`
- 在 `config.py` 中新增图表输出参数
- `main.py` 生成发端眼图、干净星座图和 PSD
- 图像输出到 `static/generated/`

图表输出：

```text
static/generated/eye.png
static/generated/constellation.png
static/generated/psd.png
```

验证结果：

```text
plot channel: QDPSK
eye trace count: 120
constellation plotted points: 6000
PSD bins: 4096
eye.png: PNG signature valid
constellation.png: PNG signature valid
psd.png: PNG signature valid
```

说明：

- 第四轮最初使用 matplotlib 时，当前 Windows conda 环境触发了 `0xc06d007f` 底层崩溃。
- 崩溃点根源是 `numpy.linalg.inv()`，不是 DSP 代码问题。
- 切换 BLAS/LAPACK 到 OpenBLAS 后，matplotlib 路径已恢复。
- 当前 `plotter.py` 使用 matplotlib Agg 生成专业图。
- 保留 `plotter_fallback.py` 作为轻量纯 Python PNG 备用渲染器。
- JS 未来仍然只负责加载这些 PNG，不参与 DSP 或图形计算。

## 第 5 轮：AWGN 与相位旋转

状态：已完成。

完成内容：

- 新增 `channel.py`
- 实现固定相位旋转
- 实现复高斯白噪声
- 实现 `apply_channel`
- 实现 `channel_summary`
- 在 `main.py` 中输出目标 SNR、相位偏移和实测估计 SNR

当前信道参数：

```text
SNR_DB = 20.0
PHASE_DEG = 0.0
```

验证结果：

```text
QPSK impaired power: 0.126467
QDPSK impaired power: 0.126341
QPSK estimated SNR dB: 20.012
QDPSK estimated SNR dB: 19.999
```

说明：

- 两路波形使用同一组信道参数。
- 眼图、干净星座图和 PSD 仍然使用干净发端波形，不被信道污染。
- 这符合蓝图里的“发端图”和“接收端图”分离原则。

## 你需要操作的测试

请在 PowerShell 中运行：

```powershell
conda activate QDRSK_TX_ELB
cd C:\Users\Rick\PycharmProjects\QDPSK\Transmitter
python main.py
```

期望看到最关键两行：

```text
SNR target dB: 20.000
QPSK estimated SNR dB: 20.012
```

## 第 7 轮：HTML GUI 静态页面

状态：已完成。

完成内容：

- 新增 `tx_pipeline.py`，把 DSP、画图、UDP 分片/发送流程从入口中抽成可复用流水线。
- 新增 `web_app.py`，使用 Python 标准库 HTTP 服务提供本地 HTML GUI 和 API。
- 新增 `templates/index.html`
- 新增 `static/app.js`
- 新增 `static/style.css`
- `main.py` 改为启动本地控制页。

说明：

- 当前环境没有安装 Flask，因此本轮先用标准库 `http.server` 实现轻量本地服务，避免新增依赖。
- HTML 不能直接双击打开使用，必须先运行 `python main.py`，再访问 `http://127.0.0.1:8000`。
- Chromium/浏览器只是界面壳，DSP、画图和 UDP 发送仍然全部由 Python 执行。

验证结果：

```text
GET /                         -> 200
GET /api/state                -> 200
GET /static/generated/eye.png -> 200
POST /api/render              -> 生成三张 PNG
POST /api/send                -> UDP packets sent: 4498
```

## 第 8 轮：HTML 控件接入 Python 后端

状态：已完成。

完成内容：

- SNR 滑块接入 `/api/config`
- Phase 滑块接入 `/api/config`
- 新增 QPSK / QDPSK 图表通道切换
- Render 按钮会先同步页面参数，再调用 Python 重新生成三张发端 PNG
- Send UDP 按钮会先同步页面参数，再调用 Python 重新生成两路 IQ、封包并发送
- 页面显示 QPSK/QDPSK symbol 数、分片包数、发送字节、耗时和估计 SNR
- 修正静态文件路径解析，避免依赖 Windows 反斜杠路径

验证结果：

```text
POST /api/config snr_db=12.5 phase_deg=45 plot_channel=QPSK -> 配置更新成功
POST /api/render -> plots.channel = QPSK
POST /api/send   -> UDP packets sent: 4498
node --check static/app.js -> 通过
python -m py_compile tx_pipeline.py web_app.py main.py -> 通过
```

## 第 9 轮：双通道并列展示

状态：已完成。

完成内容：

- 去掉 QPSK / QDPSK 二选一图表模式。
- `tx_pipeline.py` 每次同时生成 QPSK 和 QDPSK 两套图像。
- 图像输出改为：

```text
static/generated/qpsk_psd.png
static/generated/qdpsk_psd.png
static/generated/qpsk_eye.png
static/generated/qdpsk_eye.png
static/generated/qpsk_constellation.png
static/generated/qdpsk_constellation.png
```

- 前端布局改为两列三行：
  - 第一行 PSD
  - 第二行眼图
  - 第三行星座图
  - 第一列 QPSK，第二列 QDPSK
- Python 后端在 `PyCharm Terminal` 可见打印：
  - `[CONFIG]`
  - `[RENDER]`
  - `[SEND]`
  - 每次渲染/发送后的摘要统计

验证结果：

```text
python -m py_compile tx_pipeline.py web_app.py plotter.py main.py -> 通过
node --check static/app.js -> 通过
run_transmitter_pipeline(send_udp=False) -> qpsk_psd.png / qdpsk_psd.png 正常生成
static/generated/ 下六张图均存在
```

补充说明：

- 如果服务由后台进程启动，PyCharm Terminal 看不到 `[CONFIG]`、`[RENDER]`、`[SEND]` 打印。需要在 PyCharm Terminal 中直接运行 `python main.py`。
- SNR / Phase 只影响信道污染后的 IQ 和 UDP 发送统计，不影响页面展示的发端 PSD、眼图、干净星座图。
- 页面图像 URL 使用 PNG 文件纳秒级 mtime 作为版本号，Render / Send 后会强制刷新图片请求。

## 第 10 轮：信道后星座图展示

状态：已完成。

完成内容：

- 在双通道页面里新增一排信道后星座图。
- 新增输出：

```text
static/generated/qpsk_impaired_constellation.png
static/generated/qdpsk_impaired_constellation.png
```

- 这两张图来自 `apply_channel(SNR, Phase)` 之后的受损采样 IQ，会随 SNR / Phase 改变。
- 原有 PSD、眼图、干净星座图仍然来自干净发端信号。

当前 HTML 图表布局：

```text
           QPSK                              QDPSK
PSD        qpsk_psd.png                      qdpsk_psd.png
眼图       qpsk_eye.png                      qdpsk_eye.png
干净星座   qpsk_constellation.png            qdpsk_constellation.png
信道后星座 qpsk_impaired_constellation.png   qdpsk_impaired_constellation.png
```

## 第 11 轮：信道后眼图与调参优先布局

状态：已完成。

完成内容：

- 新增信道后眼图：

```text
static/generated/qpsk_impaired_eye.png
static/generated/qdpsk_impaired_eye.png
```

- 信道后眼图来自 `apply_channel(SNR, Phase)` 之后的受损 IQ。
- 页面排序调整为先显示会随 SNR / Phase 变化的图，再显示干净参考图。

当前 HTML 图表布局：

```text
           QPSK                              QDPSK
信道后星座 qpsk_impaired_constellation.png   qdpsk_impaired_constellation.png
信道后眼图 qpsk_impaired_eye.png             qdpsk_impaired_eye.png
干净 PSD   qpsk_psd.png                      qdpsk_psd.png
干净眼图   qpsk_eye.png                      qdpsk_eye.png
干净星座   qpsk_constellation.png            qdpsk_constellation.png
```

## 第 12 轮：图表字体统一为 Times New Roman

状态：已完成。

完成内容：

- 在 `plotter.py` 中统一设置 matplotlib 字体：

```python
font.family = serif
font.serif = Times New Roman
axes.unicode_minus = False
```

- 影响范围：所有 Python/matplotlib 生成的 PNG 图表标题、坐标轴标签、刻度文字。
- 当前环境已确认 Matplotlib 能找到 `Times New Roman` 字体。
- 已重新生成当前所有图表 PNG。

验证结果：

```text
python -m py_compile plotter.py tx_pipeline.py web_app.py main.py -> 通过
node --check static/app.js -> 通过
run_transmitter_pipeline(send_udp=False) -> 图表重新生成
```

后续工作建议：

- 继续完善 Transmitter 页面统计：显示 frame bytes、bit count、sample count、当前 SNR / Phase 对受损图的影响摘要。
- 可将 `TARGET_HOST` / `TARGET_PORT` 做成页面可编辑配置，但默认仍保持 `127.0.0.1:9000`。
- 可增加运行说明 `README.md`，明确必须先运行 `python main.py`，再访问 `http://127.0.0.1:8000`。
- 迁移香橙派前再补 `requirements.txt` 和 Linux/Chromium 启动说明。

## 第 13 轮：图表文字改为中文黑体

状态：已完成。

完成内容：

- matplotlib 图表字体改为黑体优先：

```text
SimHei
Microsoft YaHei
```

- 图表标题、坐标轴、页面里的图表面板标题改为中文。
- 信道后星座图、信道后眼图、干净 PSD、干净眼图、干净星座图都用中文标注。

验证结果：

```text
matplotlib font check -> SimHei available
python -m py_compile plotter.py tx_pipeline.py web_app.py main.py -> 通过
run_transmitter_pipeline(send_udp=False) -> 中文图表重新生成
```

后续工作建议：

- 如果后面香橙派字体缺失，再补字体安装或 fallback 字体策略。
- 继续完善 Transmitter 的页面统计信息和运行说明。

## 第 14 轮：移植前 Transmitter 收尾

状态：已完成。

完成内容：

- 页面新增 UDP 目标 IP 和目标端口输入框。
- `/api/config` 支持运行时更新：

```text
target_host
target_port
snr_db
phase_deg
```

- `/api/send` 使用页面当前目标地址和端口发送 UDP。
- 页面统计面板新增：

```text
图像帧字节
bit count
QPSK/QDPSK waveform sample count
frame_id
当前相位
```

- 新增 `README.md`，说明 Transmitter 运行方式、页面图表、默认参数和边界。
- 新增 `RECEIVER_INTERFACE.md`，作为 Receiver 开发对接文档。
- 清理早期遗留单图：

```text
static/generated/eye.png
static/generated/constellation.png
static/generated/psd.png
```

当前结论：

- Transmitter 在移植香橙派前的功能收尾已经完成。
- 香橙派部署应等 Receiver 开发完成、PC 本机 TX/RX 联调通过后再做。
- 下一阶段可以转入 Receiver 开发，Receiver 应优先参考 `RECEIVER_INTERFACE.md`。
# Current Update - 2026-06-15

Status: demo limits and Receiver integration synchronized.

Current image boundary:

- Source image is fixed to `raw_pic_64.png`.
- Supported payload is fixed `64x64 RGB`.
- Arbitrary image dimensions are not supported yet.

Current demo parameter limits:

```text
SNR:   6.0 .. 30.0 dB
Phase: -90 .. +90 deg
```

Implementation notes:

- `config.py` defines the clamp limits.
- `templates/index.html` slider ranges match the clamp limits.
- `static/app.js` clamps frontend values before submitting config.
- `web_app.py` clamps backend API values before updating runtime config.
- Receiver analysis can now write degraded PNGs even when a noisy QPSK path damages the `IMG0` header.
- The current Receiver can recover `qpsk_recovered.png` and `qdpsk_recovered.png` from saved captures and print MSE/PSNR.

# Current Update - 2026-06-16

Status: wider phase demo range implemented.

Scope completed:

- Changed backend phase clamp from `-30 .. +30 deg` to `-90 .. +90 deg`.
- Updated the frontend phase slider to `-90 .. +90 deg`.
- Added phase preset buttons: `0 deg`, `30 deg`, `50 deg`, `75 deg`, `-75 deg`.
- Kept SNR clamp at `6.0 .. 30.0 dB`.
- Updated demo-limit documentation and handoff notes.

Reason:

- The previous `+/-30 deg` range was too mild to clearly demonstrate QDPSK common phase-rotation tolerance.
- Recommended demo: high SNR (`25..30 dB`) and compare `0 deg`, `50 deg`, and `75 deg`.
- QPSK should degrade or fail as absolute phase crosses decision boundaries, while QDPSK should remain recoverable under a fixed common phase rotation.

Validation performed:

```powershell
F:\programs\miniconda3\envs\QDRSK_TX_ELB\python.exe -m py_compile config.py web_app.py tx_pipeline.py main.py
node --check static\app.js
```

Backend clamp smoke test:

```text
phase_deg=120 -> 90.0
phase_deg=-120 -> -90.0
```
