"""Thread-safe fixed-size circular buffer used to decouple acquisition from GUI redraws."""

from __future__ import annotations

import threading

import numpy as np


class CircularBuffer:
    """Fixed-capacity ring buffer over a 1-D numpy array.

    Acquisition code (running at ``sample_rate``, e.g. 500 Hz) pushes samples in from a
    worker thread via :meth:`push`. The GUI thread reads a snapshot via
    :meth:`get_latest` at its own, independent refresh rate. All access is guarded by a
    lock so pushes from the acquisition thread never race with GUI reads.
    """

    def __init__(self, capacity: int, fill_value: float = 0.0) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._data = np.full(capacity, fill_value, dtype=np.float64)
        self._write_index = 0
        self._filled = 0
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        return self._capacity

    def push(self, values) -> None:
        """Append one or more samples, overwriting the oldest data once full."""
        values = np.atleast_1d(np.asarray(values, dtype=np.float64))
        n = len(values)
        if n == 0:
            return
        with self._lock:
            if n >= self._capacity:
                self._data[:] = values[-self._capacity :]
                self._write_index = 0
                self._filled = self._capacity
                return
            end = self._write_index + n
            if end <= self._capacity:
                self._data[self._write_index : end] = values
            else:
                first_part = self._capacity - self._write_index
                self._data[self._write_index :] = values[:first_part]
                self._data[: end - self._capacity] = values[first_part:]
            self._write_index = end % self._capacity
            self._filled = min(self._capacity, self._filled + n)

    def get_latest(self, n: int | None = None) -> np.ndarray:
        """Return the most recent ``n`` samples (or all filled samples) in chronological order."""
        with self._lock:
            filled = self._filled
            if n is None or n > filled:
                n = filled
            if n == 0:
                return np.empty(0, dtype=np.float64)
            start = (self._write_index - n) % self._capacity
            if start + n <= self._capacity:
                return self._data[start : start + n].copy()
            first_part = self._capacity - start
            return np.concatenate((self._data[start:], self._data[: n - first_part]))

    def clear(self, fill_value: float = 0.0) -> None:
        with self._lock:
            self._data[:] = fill_value
            self._write_index = 0
            self._filled = 0
