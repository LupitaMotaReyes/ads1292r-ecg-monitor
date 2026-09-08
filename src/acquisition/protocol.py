"""Parsers for the data protocols spoken over the serial/Bluetooth link.

Two protocols are supported, both defined by THIS project (see docs/serial_protocol.md):

* ``CSVProtocolParser`` — DEBUG MODE, human-readable ASCII CSV lines of the form
  ``timestamp,ecg,respiration,status`` (e.g. ``1250,-138422,5021,0``). Intended for our
  own alternative Arduino firmware (firmware/cwxs_ads1292r_nano) running in debug mode.

* ``BinaryStreamParser`` — STREAM MODE, a compact binary frame, also defined by this
  project for our own firmware.

Neither parser understands the original, unmodified CWXS firmware protocol — that
protocol has not been reverse engineered yet. Use tools/serial_inspector.py to capture
and study what the stock CWXS PCB actually transmits before assuming either parser
applies to it.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

# UNVERIFIED: chosen for our own firmware/protocol, not the original CWXS one.
DEFAULT_BAUD_RATE = 115200


@dataclass
class Sample:
    timestamp_ms: int
    ecg_raw: int
    resp_raw: int | None
    status: int


class CSVProtocolParser:
    """Incrementally parses DEBUG MODE ASCII CSV lines from a raw byte stream."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.malformed_line_count = 0

    def feed(self, data: bytes) -> list[Sample]:
        self._buffer.extend(data)
        samples: list[Sample] = []
        while b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            sample = self._parse_line(bytes(line))
            if sample is not None:
                samples.append(sample)
        return samples

    def _parse_line(self, line: bytes) -> Sample | None:
        text = line.strip(b"\r\n \t").decode("ascii", errors="ignore").strip()
        if not text:
            return None
        parts = text.split(",")
        if len(parts) != 4:
            self.malformed_line_count += 1
            return None
        try:
            timestamp_ms, ecg_raw, resp_raw, status = (int(p) for p in parts)
        except ValueError:
            self.malformed_line_count += 1
            return None
        return Sample(timestamp_ms, ecg_raw, resp_raw, status)


# STREAM MODE binary frame layout (this project's own design):
#   offset  size  field
#   0       2     sync header, bytes 0xA5 0x5A
#   2       4     sample counter, uint32 little-endian
#   6       3     ECG, 24-bit signed little-endian (two's complement)
#   9       3     Respiration, 24-bit signed little-endian (two's complement)
#   12      1     status flags
#   13      1     checksum: XOR of bytes 0..12
FRAME_SYNC = b"\xa5\x5a"
FRAME_SIZE = 14


def _sign_extend_24(value: int) -> int:
    if value & 0x800000:
        value -= 1 << 24
    return value


class BinaryStreamParser:
    """Incrementally parses STREAM MODE binary frames, resynchronizing on corruption."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.valid_frame_count = 0
        self.corrupt_frame_count = 0

    def feed(self, data: bytes) -> list[Sample]:
        self._buffer.extend(data)
        samples: list[Sample] = []
        while True:
            sync_index = self._buffer.find(FRAME_SYNC)
            if sync_index == -1:
                if len(self._buffer) > 1:
                    del self._buffer[:-1]
                break
            if sync_index > 0:
                del self._buffer[:sync_index]
            if len(self._buffer) < FRAME_SIZE:
                break
            frame = bytes(self._buffer[:FRAME_SIZE])
            sample = self._parse_frame(frame)
            if sample is not None:
                samples.append(sample)
                self.valid_frame_count += 1
                del self._buffer[:FRAME_SIZE]
            else:
                self.corrupt_frame_count += 1
                del self._buffer[:1]
        return samples

    @staticmethod
    def _parse_frame(frame: bytes) -> Sample | None:
        checksum = 0
        for b in frame[:-1]:
            checksum ^= b
        if checksum != frame[-1]:
            return None
        counter = int.from_bytes(frame[2:6], "little", signed=False)
        ecg_raw = _sign_extend_24(int.from_bytes(frame[6:9], "little", signed=False))
        resp_raw = _sign_extend_24(int.from_bytes(frame[9:12], "little", signed=False))
        status = frame[12]
        return Sample(timestamp_ms=counter, ecg_raw=ecg_raw, resp_raw=resp_raw, status=status)


class SampleRateEstimator:
    """Measures the real incoming sample rate over a sliding time window.

    The configured/nominal sample rate (e.g. 500 Hz) should never be trusted as the
    actual rate delivered by the hardware. Feed every batch of received samples through
    :meth:`register_samples` and read :attr:`estimated_hz` for a measured value.
    """

    def __init__(self, window_s: float = 2.0) -> None:
        self._window_s = window_s
        self._events: deque[tuple[float, int]] = deque()
        self._total = 0

    def register_samples(self, n: int) -> None:
        if n <= 0:
            return
        now = time.monotonic()
        self._total += n
        self._events.append((now, n))
        cutoff = now - self._window_s
        while len(self._events) > 1 and self._events[0][0] < cutoff:
            self._events.popleft()

    @property
    def estimated_hz(self) -> float | None:
        if len(self._events) < 2:
            return None
        span = self._events[-1][0] - self._events[0][0]
        if span <= 0:
            return None
        counted = sum(n for _, n in self._events) - self._events[0][1]
        return counted / span

    @property
    def total_samples(self) -> int:
        return self._total
