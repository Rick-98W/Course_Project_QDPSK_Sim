"""Capture completed receiver frames for offline DSP work."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

from core.packet import CHANNEL_NAMES


def capture_frame(
    frame_id: int,
    channels: dict[int, np.ndarray],
    capture_dir: Path,
) -> dict[int, Path]:
    """Save completed channel IQ arrays as .npy files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    frame_dir = Path(capture_dir) / ("frame_%010d_%s" % (frame_id, timestamp))
    frame_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[int, Path] = {}
    for channel_id, iq in channels.items():
        channel_name = CHANNEL_NAMES.get(channel_id, "channel_%d" % channel_id).lower()
        output_path = frame_dir / ("%s.npy" % channel_name)
        np.save(output_path, iq)
        outputs[channel_id] = output_path
    return outputs


def format_capture_outputs(outputs: dict[int, Path]) -> str:
    parts = []
    for channel_id in sorted(outputs):
        channel_name = CHANNEL_NAMES.get(channel_id, "channel_%d" % channel_id)
        parts.append("%s=%s" % (channel_name, outputs[channel_id]))
    return ", ".join(parts)
