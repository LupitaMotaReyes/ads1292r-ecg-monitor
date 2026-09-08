"""Non-blocking serial port management: enumeration, connection, reconnection.

All serial I/O happens on a dedicated QThread so the GUI thread is never blocked.
``SerialManager`` is the object the UI talks to; it owns a QThread + ``SerialWorker``
pair and re-emits the worker's signals. Corrupt bytes are not filtered here — that is
the job of ``acquisition.protocol`` parsers; this module only moves raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from src.acquisition.protocol import DEFAULT_BAUD_RATE

__all__ = ["PortInfo", "list_ports", "guess_cwxs_port", "SerialManager", "DEFAULT_BAUD_RATE"]


@dataclass
class PortInfo:
    device: str
    description: str
    hwid: str


def list_ports() -> list[PortInfo]:
    return [
        PortInfo(device=p.device, description=p.description or "", hwid=p.hwid or "")
        for p in serial.tools.list_ports.comports()
    ]


def guess_cwxs_port(ports: list[PortInfo]) -> str | None:
    """Best-effort heuristic to pre-select the CWXS Bluetooth receiver in the port list.

    The exact VID/PID/description Windows assigns to the CWXS USB dongle is
    TO BE VERIFIED ON HARDWARE. This only looks for the word "bluetooth" (or "cwxs",
    should Windows ever surface it) in the port description, and is meant purely as a
    convenience default — the user can always pick the port manually.
    """
    for p in ports:
        desc = p.description.lower()
        if "cwxs" in desc or "bluetooth" in desc:
            return p.device
    return None


class SerialWorker(QObject):
    """Lives on a worker QThread. Polls the serial port via a QTimer so the thread's
    Qt event loop stays responsive to queued calls (e.g. ``stop``) instead of blocking
    inside a tight read loop.
    """

    data_received = Signal(bytes)
    error_occurred = Signal(str)
    connection_lost = Signal()
    port_opened = Signal()

    def __init__(self, port_name: str, baud_rate: int, poll_interval_ms: int = 5) -> None:
        super().__init__()
        self._port_name = port_name
        self._baud_rate = baud_rate
        self._poll_interval_ms = poll_interval_ms
        self._serial: serial.Serial | None = None
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        try:
            self._serial = serial.Serial(self._port_name, self._baud_rate, timeout=0)
        except (serial.SerialException, OSError) as exc:
            self.error_occurred.emit(f"Could not open {self._port_name}: {exc}")
            return
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll)
        self._timer.start(self._poll_interval_ms)
        self.port_opened.emit()

    @Slot()
    def _poll(self) -> None:
        if self._serial is None:
            return
        try:
            n = self._serial.in_waiting
            chunk = self._serial.read(n) if n else b""
            if chunk:
                self.data_received.emit(chunk)
        except (serial.SerialException, OSError) as exc:
            self.error_occurred.emit(str(exc))
            self._cleanup()
            self.connection_lost.emit()

    @Slot()
    def stop(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except (serial.SerialException, OSError):
                pass
        self._serial = None


class SerialManager(QObject):
    """GUI-facing façade over a SerialWorker running on its own QThread."""

    data_received = Signal(bytes)
    connected = Signal(str, int)
    disconnected = Signal(str)
    error = Signal(str)

    RECONNECT_DELAY_MS = 2000

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: SerialWorker | None = None
        self._port = ""
        self._baud = DEFAULT_BAUD_RATE
        self._user_requested_disconnect = True
        self.auto_reconnect = True

    @property
    def is_connected(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def connect_to_port(self, port: str, baud: int) -> None:
        if self.is_connected:
            self.disconnect_port()
        self._port = port
        self._baud = baud
        self._user_requested_disconnect = False

        self._thread = QThread()
        self._worker = SerialWorker(port, baud)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.data_received.connect(self.data_received)
        self._worker.error_occurred.connect(self.error)
        self._worker.connection_lost.connect(self._handle_connection_lost)
        self._worker.port_opened.connect(lambda: self.connected.emit(port, baud))
        self._thread.start()

    def disconnect_port(self) -> None:
        self._user_requested_disconnect = True
        self._teardown_thread()
        self.disconnected.emit("user requested")

    def _teardown_thread(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None

    def _handle_connection_lost(self) -> None:
        self._teardown_thread()
        self.disconnected.emit("connection lost")
        if self.auto_reconnect and not self._user_requested_disconnect and self._port:
            QTimer.singleShot(self.RECONNECT_DELAY_MS, self._attempt_reconnect)

    def _attempt_reconnect(self) -> None:
        if self._user_requested_disconnect or not self._port:
            return
        self.connect_to_port(self._port, self._baud)
