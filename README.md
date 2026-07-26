# 基于香橙派与 PC 的 QDPSK 通信实验

本项目是一个跨设备数字基带通信课程设计：香橙派（嵌入式 Linux）作为发送端，PC 作为接收端。系统使用 Python 完成 QPSK 与 QDPSK 信号生成、信道损伤模拟、UDP 分片传输、接收重组、解调和图像恢复，并通过网页仪表盘展示通信过程与性能指标。

> 项目研究的是数字基带算法和跨设备通信链路，不包含射频前端、MCU 外设驱动或真实无线信道硬件。

## 主要功能

- 同时生成 QPSK、QDPSK 两路 IQ 基带信号并进行对比。
- 可配置 SNR 和相位旋转，模拟加性高斯白噪声与载波相位偏差。
- 将 `complex64` IQ 采样分片封装后通过 UDP 从香橙派发送至 PC。
- PC 端完成分片重组、匹配滤波、硬判决解调和 64×64 RGB 图像恢复。
- 计算并展示 MSE、PSNR、EVM、星座图、眼图、频谱、幅度和相位等结果。
- 发送端与接收端均提供浏览器界面，便于设置参数和观察实验结果。

## 系统结构

```text
香橙派发送端（TX）                              PC 接收端（RX）
┌────────────────────┐   UDP :9000   ┌──────────────────────────────┐
│ 图像封装            │ ────────────▶ │ UDP 分片重组                  │
│ QPSK / QDPSK 调制   │               │ 匹配滤波与硬判决解调          │
│ 信道模型            │               │ 图像恢复与性能分析            │
│ Web 控制台 :8000    │               │ Web 仪表盘 :9100              │
└────────────────────┘               └──────────────────────────────┘
```

发送时，香橙派还会通过 PC 的 TCP `9100` 端口上传原始参考图像和发送端图表，供接收端计算误差指标并进行对照展示。

## 项目结构

```text
QDPSK/
├─ Transmitter/          香橙派发送端
│  ├─ analysis/          信号分析与绘图
│  ├─ core/              图像封装、调制、信道模型、分片与 UDP 发送
│  ├─ web/               发送端网页控制台
│  ├─ env_TX.yml         发送端 Conda/Miniforge 环境
│  ├─ main.py            发送端入口
│  └─ raw_pic_64.png     64×64 RGB 测试图像
├─ Receiver/             PC 接收端
│  ├─ analysis/          滤波、解调、图像恢复与性能分析
│  ├─ core/              UDP 接收、分片重组与帧管理
│  ├─ storage/           参考图像和发送端图表管理
│  ├─ tools/             离线检查与分析工具
│  ├─ web/               接收端网页仪表盘
│  ├─ env_RX.yml         接收端 Conda/Miniforge 环境
│  ├─ main.py            浏览器模式入口
│  └─ desktop_app.py     桌面窗口模式入口
├─ 课设报告.docx         可编辑课程设计报告
└─ 课设报告.pdf          PDF 课程设计报告
```

## 环境要求

- 香橙派：64 位嵌入式 Linux，建议使用 Miniforge，Python 3.10。
- PC：Windows 10/11，建议使用 Miniforge 或 Anaconda，Python 3.10。
- 两端接入同一局域网并能够互相访问。
- PC 防火墙允许 UDP `9000` 和 TCP `9100` 入站。

两份 `env_*.yml` 只列出项目直接依赖。Conda 会自动解析 NumPy、Matplotlib 等软件包所需的底层运行库，不需要把完整环境中的系统库逐项写入文件。

## 创建运行环境

### 香橙派发送端

在仓库根目录执行：

```bash
conda env create -f Transmitter/env_TX.yml
conda activate QDPSK_TX_ELB
```

### PC 接收端

在 Miniforge Prompt 或 Anaconda Prompt 中执行：

```powershell
conda env create -f Receiver/env_RX.yml
conda activate QDPSK_RX_PC
```

接收端的 `pywebview` 用于桌面窗口模式；若只运行浏览器模式，核心接收与分析功能不依赖它。

如果同名环境已经存在，可使用以下命令同步依赖：

```powershell
conda env update -f Receiver/env_RX.yml --prune
```

香橙派端同理，将文件路径替换为 `Transmitter/env_TX.yml`。

## 跨设备运行

### 1. 启动 PC 接收端

```powershell
conda activate QDPSK_RX_PC
cd Receiver
python main.py
```

浏览器访问：

```text
http://127.0.0.1:9100
```

若希望使用独立桌面窗口，可改为：

```powershell
python desktop_app.py
```

接收端监听所有本机网卡的 UDP `9000` 端口。仪表盘会显示可供香橙派使用的 PC 局域网地址。

### 2. 启动香橙派发送端

```bash
conda activate QDPSK_TX_ELB
cd Transmitter
python main.py
```

在同一局域网中的浏览器访问：

```text
http://<香橙派IP>:8000
```

在发送端页面中将目标地址设置为 PC 的局域网 IP，目标端口保持 `9000`，按需要设置 SNR 和相位角，然后发送。

### 3. 查看实验结果

接收端收到 QPSK 与 QDPSK 的完整帧后会自动进行分析，仪表盘随后显示：

- 原始图像、QPSK 恢复图像和 QDPSK 恢复图像；
- MSE、PSNR 与 EVM；
- 接收端星座图、差分星座图、眼图和频谱；
- 信号幅度、相位及各处理阶段功率。

## 单机联调

两端也可以在同一台 PC 上运行。先启动 `Receiver/main.py`，再启动 `Transmitter/main.py`，并将发送目标设置为：

```text
127.0.0.1:9000
```

## 传输协议与限制

- UDP 负载格式：`26 字节应用层头部 + complex64 IQ 采样数据`。
- 通道编号：`0` 表示 QPSK，`1` 表示 QDPSK。
- 当前演示输入固定为 `Transmitter/raw_pic_64.png`。
- 图像尺寸固定为 64×64 RGB；严重信道损伤时，接收端会按该固定尺寸尝试降级恢复。
- 本项目采用软件信道模型，SNR 与相位旋转并非来自真实射频链路测量。

## 离线验证

在接收端环境中执行分片重组检查：

```powershell
cd Receiver
python tools\offline_reassembly_check.py
```

分析最近一次接收结果：

```powershell
python tools\analyze_latest_capture.py
```

## 生成文件

接收端运行产生的抓包、恢复图像、分析报告和图表保存在 `Receiver/runtime/`。发送端生成的图表保存在 `Transmitter/web/static/generated/`。这些文件均可重新生成，因此默认不会提交到 Git。

## 课程报告

- `课设报告.docx`：可继续编辑的课程设计报告原稿。
- `课设报告.pdf`：便于在线阅读和归档的版本。

## 说明

本仓库用于课程设计归档和个人项目展示。上传至公开仓库前，请确认课程报告中不存在不希望公开的个人信息。
