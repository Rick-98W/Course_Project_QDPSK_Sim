"""Markdown export for Receiver analysis outputs."""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
from urllib.parse import quote

import config


PLOT_FILES = (
    ("qpsk_rx_constellation.png", "QPSK 接收星座图"),
    ("qdpsk_rx_constellation.png", "QDPSK 接收星座图"),
    ("qdpsk_diff_constellation.png", "QDPSK 差分星座图"),
    ("qpsk_rx_eye.png", "QPSK 接收眼图"),
    ("qdpsk_rx_eye.png", "QDPSK 接收眼图"),
    ("rx_magnitude.png", "接收波形幅度"),
    ("rx_phase.png", "接收相位轨迹"),
    ("rx_spectrum.png", "接收功率谱"),
    ("rx_evm.png", "误差矢量幅度"),
)

TX_PLOT_FILES = (
    ("tx_plots/qpsk_impaired_constellation.png", "QPSK 信道后星座图"),
    ("tx_plots/qdpsk_impaired_constellation.png", "QDPSK 信道后星座图"),
    ("tx_plots/qpsk_impaired_eye.png", "QPSK 信道后眼图"),
    ("tx_plots/qdpsk_impaired_eye.png", "QDPSK 信道后眼图"),
    ("tx_plots/qpsk_psd.png", "QPSK 信道前基带功率谱"),
    ("tx_plots/qdpsk_psd.png", "QDPSK 信道前基带功率谱"),
    ("tx_plots/qpsk_eye.png", "QPSK 信道前基带眼图"),
    ("tx_plots/qdpsk_eye.png", "QDPSK 信道前基带眼图"),
    ("tx_plots/qpsk_constellation.png", "QPSK 信道前星座图"),
    ("tx_plots/qdpsk_constellation.png", "QDPSK 信道前星座图"),
)


def export_capture_markdown(capture_dir: str | Path) -> Path:
    capture_dir = Path(capture_dir)
    summary_path = capture_dir / "capture_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError("capture summary not found: %s" % summary_path)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    output_path = capture_dir / "analysis_export.md"
    output_path.write_text(_render_markdown(capture_dir, summary), encoding="utf-8")

    config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    latest_path = config.EXPORT_DIR / "latest_analysis_export.md"
    latest_asset_dir = config.EXPORT_DIR / "latest_analysis_assets"
    _copy_latest_assets(capture_dir, latest_asset_dir)
    latest_path.write_text(
        _render_markdown(capture_dir, summary, image_prefix=latest_asset_dir.name),
        encoding="utf-8",
    )
    return output_path


def _render_markdown(capture_dir: Path, summary: dict, image_prefix: str = "") -> str:
    capture_name = str(summary.get("capture_name") or capture_dir.name)
    analyzed_at = str(summary.get("analyzed_at") or "")
    generated_at = datetime.now().isoformat(timespec="seconds")
    qpsk = summary.get("qpsk", {})
    qdpsk = summary.get("qdpsk", {})

    lines = [
        "# QDPSK 接收分析导出",
        "",
        "| 项目 | 内容 |",
        "| --- | --- |",
        "| 捕获目录 | `%s` |" % _escape_table(str(capture_dir)),
        "| 捕获名称 | `%s` |" % _escape_table(capture_name),
        "| 分析时间 | %s |" % _escape_table(analyzed_at),
        "| 导出时间 | %s |" % _escape_table(generated_at),
        "",
        "## 质量指标对照",
        "",
        _metric_table(qpsk, qdpsk),
        "",
        "## 恢复图像",
        "",
        _image_line(capture_dir, "QPSK 恢复图像", capture_dir / "qpsk_recovered.png", image_prefix),
        "",
        _image_line(capture_dir, "QDPSK 恢复图像", capture_dir / "qdpsk_recovered.png", image_prefix),
        "",
        "## 通信分析图",
        "",
    ]

    for filename, title in PLOT_FILES:
        image_path = capture_dir / filename
        if image_path.is_file():
            lines.extend([_image_line(capture_dir, title, image_path, image_prefix), ""])

    tx_lines = _tx_plot_lines(capture_dir, image_prefix)
    if tx_lines:
        lines.extend(["## 发端分析图", ""])
        lines.extend(tx_lines)

    return "\n".join(lines).rstrip() + "\n"


def _metric_table(qpsk: dict, qdpsk: dict) -> str:
    rows = [
        ("MSE", _number(qpsk.get("mse")), _number(qdpsk.get("mse"))),
        ("PSNR", _text(qpsk.get("psnr_text")), _text(qdpsk.get("psnr_text"))),
        ("IMG0 Header", _header(qpsk.get("header_valid")), _header(qdpsk.get("header_valid"))),
        ("Samples", _text(qpsk.get("sample_count")), _text(qdpsk.get("sample_count"))),
        (
            "Raw Average Power",
            _number(qpsk.get("raw_average_power")),
            _number(qdpsk.get("raw_average_power")),
        ),
        (
            "Filtered Samples",
            _text(qpsk.get("filtered_sample_count")),
            _text(qdpsk.get("filtered_sample_count")),
        ),
        (
            "Filtered Average Power",
            _number(qpsk.get("filtered_average_power")),
            _number(qdpsk.get("filtered_average_power")),
        ),
        (
            "Symbols",
            _text(qpsk.get("symbol_sample_count")),
            _text(qdpsk.get("symbol_sample_count")),
        ),
        (
            "Symbol Average Power",
            _number(qpsk.get("symbol_average_power")),
            _number(qdpsk.get("symbol_average_power")),
        ),
        ("Recovered Width", _text(qpsk.get("width")), _text(qdpsk.get("width"))),
        ("Recovered Height", _text(qpsk.get("height")), _text(qdpsk.get("height"))),
        ("Payload Bytes", _text(qpsk.get("payload_bytes")), _text(qdpsk.get("payload_bytes"))),
    ]
    body = ["| 指标 | QPSK | QDPSK |", "| --- | ---: | ---: |"]
    for metric, left, right in rows:
        body.append("| %s | %s | %s |" % (metric, _escape_table(left), _escape_table(right)))
    return "\n".join(body)


def _copy_latest_assets(capture_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for image_path in _export_image_paths(capture_dir):
        if image_path.is_file():
            (output_dir / _asset_name(image_path)).write_bytes(image_path.read_bytes())


def _export_image_paths(capture_dir: Path) -> tuple[Path, ...]:
    paths = [
        capture_dir / "qpsk_recovered.png",
        capture_dir / "qdpsk_recovered.png",
    ]
    paths.extend(capture_dir / filename for filename, _title in PLOT_FILES)
    paths.extend(capture_dir / filename for filename, _title in TX_PLOT_FILES)
    return tuple(paths)


def _image_line(base_dir: Path, title: str, image_path: Path, image_prefix: str = "") -> str:
    return "### %s\n\n![%s](%s)" % (
        title,
        title,
        _prefixed_markdown_url(image_prefix, image_path)
        if image_prefix
        else _relative_markdown_url(base_dir, image_path),
    )


def _prefixed_markdown_url(prefix: str, target: Path) -> str:
    return quote("%s/%s" % (prefix.strip("/"), _asset_name(target)), safe="/._-")


def _relative_markdown_url(base_dir: Path, target: Path) -> str:
    rel = target.resolve().relative_to(base_dir.resolve())
    return quote(str(rel).replace("\\", "/"), safe="/._-")


def _tx_plot_lines(capture_dir: Path, image_prefix: str) -> list[str]:
    lines = []
    for filename, title in TX_PLOT_FILES:
        image_path = capture_dir / filename
        if image_path.is_file():
            lines.extend([_image_line(capture_dir, title, image_path, image_prefix), ""])
    return lines


def _asset_name(path: Path) -> str:
    if path.parent.name == "tx_plots":
        return "tx_" + path.name
    return path.name


def _number(value) -> str:
    if value is None:
        return "--"
    number = float(value)
    if math.isinf(number):
        return "inf"
    return "%.6f" % number


def _text(value) -> str:
    return "--" if value is None else str(value)


def _header(value) -> str:
    if value is True:
        return "valid"
    if value is False:
        return "fallback"
    return "--"


def _escape_table(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
