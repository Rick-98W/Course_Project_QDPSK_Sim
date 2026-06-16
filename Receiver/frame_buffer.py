"""Frame reassembly for dual-channel UDP IQ streams."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from packet import CHANNEL_NAMES, FragmentHeader, PacketError, payload_to_complex64


@dataclass
class ChannelFrame:
    frame_id: int
    channel_id: int
    chunk_count: int
    total_samples: int
    chunks: dict[int, bytes] = field(default_factory=dict)
    duplicate_chunks: int = 0
    last_reported_chunks: int = 0
    last_reported_percent: int = 0

    @property
    def channel_name(self) -> str:
        return CHANNEL_NAMES.get(self.channel_id, "UNKNOWN")

    @property
    def received_count(self) -> int:
        return len(self.chunks)

    @property
    def is_complete(self) -> bool:
        return self.received_count == self.chunk_count

    def add_fragment(self, header: FragmentHeader, payload: bytes) -> bool:
        self._validate_header_consistency(header)
        if header.chunk_index in self.chunks:
            self.duplicate_chunks += 1
            return False
        self.chunks[header.chunk_index] = payload
        return True

    def _validate_header_consistency(self, header: FragmentHeader) -> None:
        if header.frame_id != self.frame_id:
            raise PacketError("frame_id changed inside channel frame")
        if header.channel_id != self.channel_id:
            raise PacketError("channel_id changed inside channel frame")
        if header.chunk_count != self.chunk_count:
            raise PacketError(
                "chunk_count conflict for frame=%d channel=%s: %d vs %d"
                % (
                    self.frame_id,
                    self.channel_name,
                    self.chunk_count,
                    header.chunk_count,
                )
            )
        if header.total_samples != self.total_samples:
            raise PacketError(
                "total_samples conflict for frame=%d channel=%s: %d vs %d"
                % (
                    self.frame_id,
                    self.channel_name,
                    self.total_samples,
                    header.total_samples,
                )
            )

    def should_report_progress(self, chunk_step: int, percent_step: int) -> bool:
        if self.is_complete:
            return True

        count_delta = self.received_count - self.last_reported_chunks
        percent = int((self.received_count * 100) // self.chunk_count)
        percent_delta = percent - self.last_reported_percent
        return count_delta >= chunk_step or percent_delta >= percent_step

    def mark_reported(self) -> None:
        self.last_reported_chunks = self.received_count
        self.last_reported_percent = int((self.received_count * 100) // self.chunk_count)

    def progress_line(self) -> str:
        percent = (self.received_count * 100.0) / self.chunk_count
        return (
            "frame_id=%d channel=%s chunks=%d/%d %.1f%% duplicates=%d"
            % (
                self.frame_id,
                self.channel_name,
                self.received_count,
                self.chunk_count,
                percent,
                self.duplicate_chunks,
            )
        )

    def reassemble_payload(self) -> bytes:
        if not self.is_complete:
            raise PacketError(
                "frame=%d channel=%s incomplete: %d/%d"
                % (
                    self.frame_id,
                    self.channel_name,
                    self.received_count,
                    self.chunk_count,
                )
            )

        missing = [index for index in range(self.chunk_count) if index not in self.chunks]
        if missing:
            raise PacketError(
                "frame=%d channel=%s missing chunks: %s"
                % (self.frame_id, self.channel_name, missing[:10])
            )
        return b"".join(self.chunks[index] for index in range(self.chunk_count))

    def reassemble_iq(self) -> np.ndarray:
        iq = payload_to_complex64(self.reassemble_payload())
        if len(iq) != self.total_samples:
            raise PacketError(
                "sample count mismatch for frame=%d channel=%s: %d vs %d"
                % (self.frame_id, self.channel_name, len(iq), self.total_samples)
            )
        return iq


class FrameBuffer:
    """Collect UDP fragments until each channel can be reassembled."""

    def __init__(self, expected_channels=(0, 1)):
        self.expected_channels = tuple(expected_channels)
        self.frames: dict[tuple[int, int], ChannelFrame] = {}
        self.completed_keys: set[tuple[int, int]] = set()

    def add_fragment(self, header: FragmentHeader, payload: bytes) -> tuple[ChannelFrame, bool]:
        key = header.key
        if key not in self.frames:
            self.frames[key] = ChannelFrame(
                frame_id=header.frame_id,
                channel_id=header.channel_id,
                chunk_count=header.chunk_count,
                total_samples=header.total_samples,
            )

        channel_frame = self.frames[key]
        is_new = channel_frame.add_fragment(header, payload)
        if channel_frame.is_complete:
            self.completed_keys.add(key)
        return channel_frame, is_new

    def frame_complete(self, frame_id: int) -> bool:
        return all((frame_id, channel_id) in self.completed_keys for channel_id in self.expected_channels)

    def get_completed_frame(self, frame_id: int) -> dict[int, np.ndarray]:
        if not self.frame_complete(frame_id):
            raise PacketError("frame_id=%d is not complete for all channels" % frame_id)
        return {
            channel_id: self.frames[(frame_id, channel_id)].reassemble_iq()
            for channel_id in self.expected_channels
        }

    def drop_frame(self, frame_id: int) -> None:
        for channel_id in self.expected_channels:
            key = (frame_id, channel_id)
            self.frames.pop(key, None)
            self.completed_keys.discard(key)

    def pending_frames(self) -> list[ChannelFrame]:
        return sorted(self.frames.values(), key=lambda frame: (frame.frame_id, frame.channel_id))
