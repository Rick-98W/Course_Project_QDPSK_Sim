"""Helpers for writing human-readable packet previews to disk."""

from __future__ import annotations

from pathlib import Path

from core.packet import format_fragment_preview


def write_packet_preview(output_path, packet_bytes, label):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = [
        "# Packet Preview",
        "label=%s" % label,
        format_fragment_preview(packet_bytes),
        "",
    ]
    output.write_text("\n".join(text), encoding="utf-8")
    return str(output)
