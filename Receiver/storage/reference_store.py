"""Store the transmitter-provided reference image on the Receiver side."""

from __future__ import annotations

from pathlib import Path

import config
from analysis.reference_image import load_reference_image


def save_reference_png(data: bytes, output_path: str | Path = config.REFERENCE_IMAGE_PATH):
    if len(data) > int(config.MAX_REFERENCE_IMAGE_BYTES):
        raise ValueError("reference image is too large")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    reference = load_reference_image(path)
    if reference.width != 64 or reference.height != 64 or reference.channels != 3:
        path.unlink(missing_ok=True)
        raise ValueError("reference image must be 64x64 RGB/RGBA PNG")
    return reference


def reference_available(path: str | Path = config.REFERENCE_IMAGE_PATH) -> bool:
    return Path(path).is_file()
