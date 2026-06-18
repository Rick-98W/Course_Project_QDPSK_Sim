"""Store transmitter-side analysis plots uploaded by TX."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

import config


TX_PLOT_FILES = (
    ("qpsk_impaired_constellation.png", "QPSK 信道后星座图"),
    ("qdpsk_impaired_constellation.png", "QDPSK 信道后星座图"),
    ("qpsk_impaired_eye.png", "QPSK 信道后眼图"),
    ("qdpsk_impaired_eye.png", "QDPSK 信道后眼图"),
    ("qpsk_psd.png", "QPSK 信道前基带功率谱"),
    ("qdpsk_psd.png", "QDPSK 信道前基带功率谱"),
    ("qpsk_eye.png", "QPSK 信道前基带眼图"),
    ("qdpsk_eye.png", "QDPSK 信道前基带眼图"),
    ("qpsk_constellation.png", "QPSK 信道前星座图"),
    ("qdpsk_constellation.png", "QDPSK 信道前星座图"),
)
TX_METADATA_FILE = "tx_metadata.json"


def save_tx_plot_zip(data: bytes, output_dir: str | Path = config.TX_PLOT_DIR) -> dict:
    if len(data) > int(config.MAX_TX_PLOTS_BYTES):
        raise ValueError("TX plot package is too large")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(_bytes_path(data)) as archive:
        names = set(archive.namelist())
        missing = [filename for filename, _title in TX_PLOT_FILES if filename not in names]
        if missing:
            raise ValueError("TX plot package missing files: %s" % ", ".join(missing))
        if "metadata.json" in names:
            metadata = _read_tx_metadata(archive.read("metadata.json"))
            (output / TX_METADATA_FILE).write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            stale_metadata = output / TX_METADATA_FILE
            if stale_metadata.is_file():
                stale_metadata.unlink()
        for filename, _title in TX_PLOT_FILES:
            payload = archive.read(filename)
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("TX plot is not PNG: %s" % filename)
            (output / filename).write_bytes(payload)
    return tx_plot_asset_map(output)


def copy_tx_plots_to_capture(capture_dir: str | Path) -> dict:
    source = Path(config.TX_PLOT_DIR)
    if not source.is_dir():
        return {}
    target = Path(capture_dir) / "tx_plots"
    target.mkdir(parents=True, exist_ok=True)
    copied = {}
    source_metadata = source / TX_METADATA_FILE
    if source_metadata.is_file():
        target_metadata = target / TX_METADATA_FILE
        shutil.copyfile(source_metadata, target_metadata)
        copied["tx_metadata"] = str(target_metadata)
    for filename, title in TX_PLOT_FILES:
        source_path = source / filename
        if source_path.is_file():
            target_path = target / filename
            shutil.copyfile(source_path, target_path)
            copied["tx_" + Path(filename).stem] = str(target_path)
    return copied


def tx_plot_asset_map(root: str | Path = config.TX_PLOT_DIR) -> dict:
    root = Path(root)
    assets = {}
    metadata_path = root / TX_METADATA_FILE
    if metadata_path.is_file():
        assets["tx_metadata"] = str(metadata_path)
    for filename, title in TX_PLOT_FILES:
        path = root / filename
        if path.is_file():
            assets["tx_" + Path(filename).stem] = str(path)
    return assets


def latest_tx_metadata(root: str | Path = config.TX_PLOT_DIR) -> dict:
    path = Path(root) / TX_METADATA_FILE
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_tx_metadata(payload: bytes) -> dict:
    metadata = json.loads(payload.decode("utf-8"))
    return {
        "snr_db": float(metadata["snr_db"]),
        "phase_deg": float(metadata["phase_deg"]),
        "frame_id": int(metadata["frame_id"]),
        "generated_at": metadata.get("generated_at"),
    }


def _bytes_path(data: bytes):
    from io import BytesIO

    return BytesIO(data)
