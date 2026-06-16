"""Offline sanity check for Receiver packet parsing and capture output."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from capture import capture_frame
from frame_buffer import FrameBuffer
from packet import (
    CHANNEL_QDPSK,
    CHANNEL_QPSK,
    HEADER_STRUCT,
    MAGIC,
    MODE_DUAL_CHANNEL,
    SAMPLE_FORMAT_COMPLEX64,
    VERSION,
    parse_fragment,
)


def build_packet(frame_id, channel_id, chunk_index, chunk_count, start_sample, total_samples, samples):
    payload = np.asarray(samples, dtype=np.complex64).tobytes()
    header = HEADER_STRUCT.pack(
        MAGIC,
        MODE_DUAL_CHANNEL,
        VERSION,
        int(frame_id),
        int(channel_id),
        SAMPLE_FORMAT_COMPLEX64,
        int(chunk_index),
        int(chunk_count),
        int(start_sample),
        int(total_samples),
        len(payload) // 8,
    )
    return header + payload


def main() -> int:
    frame_id = 123
    chunk_count = 3
    total_samples = 6
    expected = {
        CHANNEL_QPSK: np.array([1 + 2j, 3 + 4j, 5 + 6j, 7 + 8j, 9 + 10j, 11 + 12j], dtype=np.complex64),
        CHANNEL_QDPSK: np.array([2 + 1j, 4 + 3j, 6 + 5j, 8 + 7j, 10 + 9j, 12 + 11j], dtype=np.complex64),
    }

    frame_buffer = FrameBuffer(expected_channels=(CHANNEL_QPSK, CHANNEL_QDPSK))
    for channel_id, iq in expected.items():
        packets = [
            build_packet(frame_id, channel_id, 0, chunk_count, 0, total_samples, iq[0:2]),
            build_packet(frame_id, channel_id, 1, chunk_count, 2, total_samples, iq[2:4]),
            build_packet(frame_id, channel_id, 2, chunk_count, 4, total_samples, iq[4:6]),
        ]
        for packet in (packets[1], packets[0], packets[2]):
            header, payload = parse_fragment(packet)
            frame_buffer.add_fragment(header, payload)

    if not frame_buffer.frame_complete(frame_id):
        raise AssertionError("frame did not complete")

    channels = frame_buffer.get_completed_frame(frame_id)
    for channel_id, expected_iq in expected.items():
        np.testing.assert_array_equal(channels[channel_id], expected_iq)

    output_dir = PROJECT_DIR / "tmp_offline_check"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    outputs = capture_frame(frame_id, channels, output_dir)
    for channel_id, output_path in outputs.items():
        loaded = np.load(output_path)
        np.testing.assert_array_equal(loaded, expected[channel_id])
    shutil.rmtree(output_dir)

    print("offline reassembly check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
