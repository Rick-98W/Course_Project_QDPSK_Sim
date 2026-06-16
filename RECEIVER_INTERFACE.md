# Receiver 对接文档

本文档给 Receiver 开发使用。Receiver 必须按这里的协议和参数对齐 Transmitter。

## 数据链路

Transmitter 发送到 Receiver 的不是原图，也不是 bitstream，而是：

```text
RRC 成型后 -> AWGN + Phase 后 -> complex64 采样级数字基带 I/Q
```

默认目标：

```text
host = 127.0.0.1
port = 9000
```

页面可以临时修改目标 IP 和端口。PC 本机联调时先保持 `127.0.0.1:9000`。

## 固定信源

```text
image = raw_pic_64.png
width = 64
height = 64
channels = 3
raw RGB payload bytes = 12288
image frame bytes = 12297
bit count = 98376
```

图像通信帧格式：

```text
magic:     4 bytes, b"IMG0"
width:     uint16, big-endian
height:    uint16, big-endian
channels:  uint8, fixed 3
payload:   RGB raw bytes
```

注意：这个图像帧在 Transmitter 内部用于生成 bitstream。UDP 当前不直接发送这个图像帧。

## 调制参数

```text
SAMPLES_PER_SYMBOL = 8
RRC_BETA = 0.35
RRC_SPAN = 8
RRC tap count = 65
RRC filter delay samples = 32
```

QPSK Gray 映射：

```text
00 ->  1 + 1j
01 -> -1 + 1j
11 -> -1 - 1j
10 ->  1 - 1j
```

所有星座点除以 `sqrt(2)`，归一化到单位平均功率。

QDPSK 差分规则：

```text
bits -> dibits -> phase_step in {0,1,2,3}
phase[k] = (phase_step[k] + phase[k-1]) mod 4
phase -> QPSK constellation symbol
```

Receiver 后续如果要解调，必须使用完全一致的映射和差分规则。

## 默认一帧规模

当前默认输出：

```text
QPSK symbol count = 49188
QDPSK symbol count = 49188
QPSK waveform sample count = 393568
QDPSK waveform sample count = 393568
```

每个采样点格式：

```text
complex64 = float32 real + float32 imag
bytes per sample = 8
```

单路 payload 约：

```text
393568 * 8 = 3148544 bytes
```

双路 payload 约：

```text
6297088 bytes
```

## UDP 分片协议

每个 UDP datagram 是一个独立分片：

```text
application_header + complex64_payload
```

Header 使用 Python struct：

```python
struct.Struct(">2sBBIBBHHIII")
```

字节序：big-endian。

字段：

```text
magic          2 bytes  b"\xAA\xBB"
mode           uint8    0x03，双通道模式
version        uint8    0x01
frame_id       uint32   同一帧图像的两路分片共用同一个 frame_id
channel_id     uint8    0 = QPSK, 1 = QDPSK
sample_format  uint8    1 = complex64
chunk_index    uint16   当前分片序号，0-based
chunk_count    uint16   当前通道总分片数
start_sample   uint32   当前分片起始 sample index
total_samples  uint32   当前通道总 sample 数
chunk_samples  uint32   当前分片 sample 数
payload         bytes   complex64 IQ payload
```

Header 长度：

```text
26 bytes
```

默认 payload 上限：

```text
UDP_FRAGMENT_PAYLOAD_BYTES = 1400
```

因为 `complex64` 每点 8 bytes，实际每个满载分片：

```text
payload bytes = 1400
chunk_samples = 175
datagram bytes = 1426
```

默认一帧分片数量：

```text
QPSK chunk_count = 2249
QDPSK chunk_count = 2249
total UDP packets = 4498
```

最后一个分片 payload 可能小于 1400 bytes。

## Receiver 重组建议

Receiver 先只做收包和重组，不要急着解调。

推荐 key：

```text
(frame_id, channel_id)
```

每个 key 下保存：

```text
chunk_count
total_samples
chunks[chunk_index] = payload
```

基本校验：

```text
magic == b"\xAA\xBB"
mode == 0x03
version == 0x01
sample_format == 1
channel_id in {0, 1}
payload_bytes % 8 == 0
chunk_samples == payload_bytes / 8
start_sample == sum(previous chunk_samples) for normal ordered chunks
```

UDP 可能乱序，所以不要假设按序到达。应按 `chunk_index` 重组。

重组完成条件：

```text
received chunk count == chunk_count
```

重组后：

```python
iq = np.frombuffer(joined_payload, dtype=np.complex64)
```

再校验：

```text
len(iq) == total_samples
total_samples == 393568  # 当前默认参数
```

## 调试参考

Transmitter 每次生成预览文件：

```text
static/generated/qpsk_packet_preview.txt
static/generated/qdpsk_packet_preview.txt
```

里面包含首包 header、前几个 complex64 样本和 payload hex，可用于 Receiver 解析对照。

典型首包：

```text
magic=b'\xaa\xbb'
mode=3
version=1
channel_id=0 或 1
sample_format=1
chunk_index=0/2249
start_sample=0
chunk_samples=175
total_samples=393568
payload_bytes=1400
```

## 开发阶段建议

1. 先写最小 UDP listener，绑定 `127.0.0.1:9000`。
2. 点击 Transmitter 页面 `发送 UDP`。
3. Receiver 打印每个 channel 的 chunk 接收进度。
4. 两路都收到 2249 片后重组为 `complex64`。
5. 打印两路：

```text
dtype
sample count
average power
estimated payload bytes
```

6. 重组稳定后，再开始做同步、解调、差分解码和图像恢复。

## 不要改的边界

- 不要让 Receiver 假设 UDP 里是原图 bytes。
- 不要让 Receiver 假设 UDP 里是 bitstream。
- 不要把 QPSK / QDPSK 当成单路二选一；两路会同时发送。
- 不要在链路闭环前引入 `int16` 量化，当前 sample_format 固定为 `complex64`。
# Current Interface Update - 2026-06-15

Receiver is now implemented and working against the current Transmitter protocol.

Current data path:

```text
RRC-shaped IQ -> AWGN + phase rotation -> complex64 UDP fragments -> Receiver reassembly -> capture analysis -> PNG recovery
```

Current Receiver capabilities:

- UDP receive on `127.0.0.1:9000`
- 26-byte fragmented header parse
- QPSK/QDPSK `complex64` reassembly
- capture writing under `Receiver/captures/frame_*/`
- offline matched filtering and fixed-timing sampling
- hard-decision QPSK and differential QDPSK demodulation
- `IMG0` image recovery
- `qpsk_recovered.png` and `qdpsk_recovered.png` output
- MSE/PSNR comparison against `Transmitter/raw_pic_64.png`

Current demo boundary:

```text
source image: raw_pic_64.png
dimensions: 64x64 RGB
fallback recovery: fixed 64x64x3 RGB
SNR clamp:   6.0 .. 30.0 dB
Phase clamp: -30 .. +30 deg
```

Arbitrary image dimensions are not supported yet.
