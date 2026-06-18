"""Static HTML report generation for receiver capture analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote

import config


@dataclass(frozen=True)
class ChannelReport:
    name: str
    capture_path: Path
    recovered_png: Path
    sample_count: int
    raw_average_power: float
    filtered_sample_count: int
    filtered_average_power: float
    symbol_sample_count: int
    symbol_average_power: float
    width: int
    height: int
    channels: int
    payload_bytes: int
    header_valid: bool
    mse: float
    psnr: float


@dataclass(frozen=True)
class PlotReport:
    title: str
    detail: str
    image_path: Path


@dataclass(frozen=True)
class CaptureIndexEntry:
    capture_name: str
    capture_dir: Path
    analyzed_at: str
    report_path: Path
    qpsk_mse: float
    qpsk_psnr: str
    qpsk_header_valid: bool
    qdpsk_mse: float
    qdpsk_psnr: str
    qdpsk_header_valid: bool


def write_capture_report(
    output_path: str | Path,
    reference_png: str | Path,
    qpsk: ChannelReport,
    qdpsk: ChannelReport,
    plots: tuple[PlotReport, ...] = (),
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = _render_report(output.parent, Path(reference_png), qpsk, qdpsk, plots)
    output.write_text(html, encoding="utf-8")
    return output


def write_capture_summary(
    output_path: str | Path,
    reference_png: str | Path,
    qpsk: ChannelReport,
    qdpsk: ChannelReport,
    report_path: str | Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "capture_name": qpsk.capture_path.parent.name,
        "capture_dir": str(qpsk.capture_path.parent),
        "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report_path": str(Path(report_path)),
        "reference_path": str(Path(reference_png)),
        "qpsk": _channel_payload(qpsk),
        "qdpsk": _channel_payload(qdpsk),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def load_capture_index_entries(capture_root: str | Path) -> list[CaptureIndexEntry]:
    root = Path(capture_root)
    entries: list[CaptureIndexEntry] = []
    for summary_path in root.glob("frame_*/capture_summary.json"):
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            entries.append(_summary_to_index_entry(summary_path, data))
        except Exception:
            continue
    entries.sort(key=lambda item: item.analyzed_at, reverse=True)
    return entries


def write_capture_index(output_path: str | Path, capture_root: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = load_capture_index_entries(capture_root)
    html = _render_index(output.parent, Path(capture_root), entries)
    output.write_text(html, encoding="utf-8")
    return output


def _render_report(
    base_dir: Path,
    reference_png: Path,
    qpsk: ChannelReport,
    qdpsk: ChannelReport,
    plots: tuple[PlotReport, ...],
) -> str:
    capture_name = qpsk.capture_path.parent.name
    figures = "\n      ".join(
        [
            _figure(base_dir, "Original", "reference", reference_png),
            _figure(base_dir, "QPSK", _quality_label(qpsk), qpsk.recovered_png),
            _figure(base_dir, "QDPSK", _quality_label(qdpsk), qdpsk.recovered_png),
        ]
    )
    plot_section = _plot_section(base_dir, plots)
    summary_table = _summary_table(qpsk, qdpsk)
    font_family = config.UI_FONT_FAMILY
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Receiver Capture Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #18202a;
      --muted: #66717f;
      --line: #d8dee7;
      --accent: #0f766e;
      --bad: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: {font_family};
      color: var(--text);
      background: var(--bg);
    }}
    header {{
      padding: 24px clamp(16px, 4vw, 44px) 14px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(24px, 3vw, 36px);
      font-weight: 700;
      letter-spacing: 0;
    }}
    .sub {{
      color: var(--muted);
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    main {{
      width: min(1180px, 100%);
      margin: 0 auto;
      padding: 22px clamp(14px, 3vw, 28px) 34px;
    }}
    .images {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      align-items: start;
    }}
    .plots {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      align-items: start;
      margin-top: 18px;
    }}
    figure {{
      margin: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    figcaption {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      font-weight: 650;
      font-size: 14px;
    }}
    figcaption span {{
      color: var(--muted);
      font-weight: 500;
    }}
    img {{
      display: block;
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: contain;
      image-rendering: pixelated;
      background: #111827;
    }}
    .plots img {{
      aspect-ratio: 45 / 31;
      image-rendering: auto;
      background: #f6f7f9;
    }}
    table {{
      width: 100%;
      margin-top: 18px;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef2f7;
      font-weight: 700;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .ok {{ color: var(--accent); font-weight: 700; }}
    .warn {{ color: var(--bad); font-weight: 700; }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 820px) {{
      .images, .plots {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Receiver Capture Report</h1>
    <div class="sub"><code>{capture_name}</code></div>
  </header>
  <main>
    <section class="images" aria-label="Recovered image comparison">
      {figures}
    </section>
    {plot_section}
    {summary_table}
  </main>
</body>
</html>
""".format(
        capture_name=escape(capture_name),
        figures=figures,
        plot_section=plot_section,
        summary_table=summary_table,
        font_family=font_family,
    )


def _render_index(base_dir: Path, capture_root: Path, entries: list[CaptureIndexEntry]) -> str:
    rows = []
    for entry in entries:
        rows.append(
            "<tr>"
            "<td><code>{capture}</code></td>"
            "<td>{analyzed}</td>"
            "<td>{qpsk}</td>"
            "<td>{qdpsk}</td>"
            "<td>{qpsk_header}</td>"
            "<td>{qdpsk_header}</td>"
            "<td><a href=\"{report}\">open</a></td>"
            "</tr>".format(
                capture=escape(entry.capture_name),
                analyzed=escape(entry.analyzed_at),
                qpsk=_metric_cell(entry.qpsk_mse, entry.qpsk_psnr),
                qdpsk=_metric_cell(entry.qdpsk_mse, entry.qdpsk_psnr),
                qpsk_header=_status_cell(entry.qpsk_header_valid),
                qdpsk_header=_status_cell(entry.qdpsk_header_valid),
                report=escape(_relative_url(base_dir, entry.report_path)),
            )
        )

    latest_block = ""
    if entries:
        latest = entries[0]
        latest_block = """
    <section class="latest">
      <div class="card">
        <div class="kicker">Latest analyzed capture</div>
        <div class="name"><code>{capture}</code></div>
        <div class="meta">{analyzed}</div>
        <div class="links"><a href="{report}">Open report</a></div>
      </div>
    </section>
""".format(
            capture=escape(latest.capture_name),
            analyzed=escape(latest.analyzed_at),
            report=escape(_relative_url(base_dir, latest.report_path)),
        )

    table_body = "\n".join(rows) if rows else '<tr><td colspan="7">No analyzed captures yet.</td></tr>'
    font_family = config.UI_FONT_FAMILY
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Receiver Capture Index</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #18202a;
      --muted: #66717f;
      --line: #d8dee7;
      --accent: #0f766e;
      --bad: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: {font_family};
      color: var(--text);
      background: var(--bg);
    }}
    header {{
      padding: 24px clamp(16px, 4vw, 44px) 14px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(24px, 3vw, 36px);
    }}
    .sub {{
      color: var(--muted);
      font-size: 14px;
    }}
    main {{
      width: min(1280px, 100%);
      margin: 0 auto;
      padding: 22px clamp(14px, 3vw, 28px) 34px;
    }}
    .latest {{
      margin-bottom: 18px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .kicker {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
      margin-bottom: 8px;
    }}
    .name {{
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .meta, .subtle {{
      color: var(--muted);
      font-size: 14px;
    }}
    .links {{
      margin-top: 10px;
    }}
    .links a, table a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef2f7;
      font-weight: 700;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .ok {{ color: var(--accent); font-weight: 700; }}
    .warn {{ color: var(--bad); font-weight: 700; }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 900px) {{
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Receiver Capture Index</h1>
    <div class="sub">Static reports generated from analyzed captures in <code>{capture_root}</code></div>
  </header>
  <main>
    {latest_block}
    <table>
      <thead>
        <tr>
          <th>Capture</th>
          <th>Analyzed</th>
          <th>QPSK</th>
          <th>QDPSK</th>
          <th>QPSK Header</th>
          <th>QDPSK Header</th>
          <th>Report</th>
        </tr>
      </thead>
      <tbody>
        {table_body}
      </tbody>
    </table>
  </main>
</body>
</html>
""".format(
        capture_root=escape(str(capture_root)),
        latest_block=latest_block,
        table_body=table_body,
        font_family=font_family,
    )


def _figure(base_dir: Path, title: str, detail: str, image_path: Path) -> str:
    return """<figure>
        <figcaption>{title} <span>{detail}</span></figcaption>
        <img src="{src}" alt="{title}">
      </figure>""".format(
        title=escape(title),
        detail=escape(detail),
        src=escape(_relative_url(base_dir, image_path)),
    )


def _plot_section(base_dir: Path, plots: tuple[PlotReport, ...]) -> str:
    if not plots:
        return ""
    figures = "\n      ".join(
        _figure(base_dir, plot.title, plot.detail, plot.image_path) for plot in plots
    )
    return """<section class="plots" aria-label="Receiver communication plots">
      {figures}
    </section>""".format(figures=figures)


def _summary_table(qpsk: ChannelReport, qdpsk: ChannelReport) -> str:
    rows = [
        ("Capture file", _code(str(qpsk.capture_path)), _code(str(qdpsk.capture_path))),
        ("Samples", str(qpsk.sample_count), str(qdpsk.sample_count)),
        ("Raw average power", _float(qpsk.raw_average_power), _float(qdpsk.raw_average_power)),
        (
            "Filtered samples",
            str(qpsk.filtered_sample_count),
            str(qpsk.filtered_sample_count),
        ),
        (
            "Filtered average power",
            _float(qpsk.filtered_average_power),
            _float(qdpsk.filtered_average_power),
        ),
        ("Symbols", str(qpsk.symbol_sample_count), str(qdpsk.symbol_sample_count)),
        (
            "Symbol average power",
            _float(qpsk.symbol_average_power),
            _float(qdpsk.symbol_average_power),
        ),
        ("Recovered image", _image_dims(qpsk), _image_dims(qdpsk)),
        ("IMG0 header", _header_status(qpsk), _header_status(qdpsk)),
        ("MSE", _float(qpsk.mse), _float(qdpsk.mse)),
        ("PSNR", _psnr(qpsk.psnr), _psnr(qdpsk.psnr)),
    ]
    body = "\n".join(
        "<tr><td>{label}</td><td>{left}</td><td>{right}</td></tr>".format(
            label=escape(label), left=left, right=right
        )
        for label, left, right in rows
    )
    return """<table>
      <thead><tr><th>Metric</th><th>QPSK</th><th>QDPSK</th></tr></thead>
      <tbody>
        {body}
      </tbody>
    </table>""".format(body=body)


def _quality_label(channel: ChannelReport) -> str:
    return "MSE %s / PSNR %s" % (_float(channel.mse), _psnr(channel.psnr))


def _image_dims(channel: ChannelReport) -> str:
    return "%dx%d, channels=%d, payload=%d" % (
        channel.width,
        channel.height,
        channel.channels,
        channel.payload_bytes,
    )


def _header_status(channel: ChannelReport) -> str:
    css = "ok" if channel.header_valid else "warn"
    text = "valid" if channel.header_valid else "fallback"
    return '<span class="%s">%s</span>' % (css, text)


def _float(value: float) -> str:
    return "%.6f" % value


def _psnr(value: float) -> str:
    if value == float("inf"):
        return "inf"
    return "%.3f dB" % value


def _code(value: str) -> str:
    return "<code>%s</code>" % escape(value)


def _relative_url(base_dir: Path, target: Path) -> str:
    rel = os.path.relpath(Path(target), Path(base_dir))
    return quote(rel.replace(os.sep, "/"), safe="/._-:")


def _channel_payload(channel: ChannelReport) -> dict:
    return {
        "sample_count": channel.sample_count,
        "raw_average_power": channel.raw_average_power,
        "filtered_sample_count": channel.filtered_sample_count,
        "filtered_average_power": channel.filtered_average_power,
        "symbol_sample_count": channel.symbol_sample_count,
        "symbol_average_power": channel.symbol_average_power,
        "width": channel.width,
        "height": channel.height,
        "channels": channel.channels,
        "payload_bytes": channel.payload_bytes,
        "header_valid": channel.header_valid,
        "mse": channel.mse,
        "psnr": None if channel.psnr == float("inf") else channel.psnr,
        "psnr_text": _psnr(channel.psnr),
        "recovered_png": str(channel.recovered_png),
    }


def _summary_to_index_entry(summary_path: Path, data: dict) -> CaptureIndexEntry:
    qpsk = data.get("qpsk", {})
    qdpsk = data.get("qdpsk", {})
    capture_dir = Path(data.get("capture_dir", summary_path.parent))
    report_path = Path(data.get("report_path", summary_path.parent / "capture_report.html"))
    return CaptureIndexEntry(
        capture_name=str(data.get("capture_name", summary_path.parent.name)),
        capture_dir=capture_dir,
        analyzed_at=str(data.get("analyzed_at", summary_path.stat().st_mtime)),
        report_path=report_path,
        qpsk_mse=float(qpsk.get("mse", 0.0)),
        qpsk_psnr=str(qpsk.get("psnr_text", "n/a")),
        qpsk_header_valid=bool(qpsk.get("header_valid", False)),
        qdpsk_mse=float(qdpsk.get("mse", 0.0)),
        qdpsk_psnr=str(qdpsk.get("psnr_text", "n/a")),
        qdpsk_header_valid=bool(qdpsk.get("header_valid", False)),
    )


def _metric_cell(mse: float, psnr: str) -> str:
    return '<div><code>%s</code></div><div class="subtle">%s</div>' % (
        _float(mse),
        escape(psnr),
    )


def _status_cell(valid: bool) -> str:
    css = "ok" if valid else "warn"
    text = "valid" if valid else "fallback"
    return '<span class="%s">%s</span>' % (css, text)
