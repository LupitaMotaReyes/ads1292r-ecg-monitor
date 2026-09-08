#!/usr/bin/env python3
"""Serial protocol diagnostic tool.

Use this BEFORE assuming any protocol about the stock CWXS firmware. It opens a COM
port, prints every byte received as a hex dump (with a best-effort ASCII column),
measures throughput, and can save a raw binary capture for later analysis.

Examples:
    python tools/serial_inspector.py --list
    python tools/serial_inspector.py --port COM7 --baud 115200
    python tools/serial_inspector.py --port COM7 --baud 115200 --out capture.bin

Press Ctrl+C to stop.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import serial
import serial.tools.list_ports

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.acquisition.protocol import DEFAULT_BAUD_RATE, FRAME_SYNC  # noqa: E402

SUPPORTED_BAUD_RATES = (9600, 57600, 115200, 230400, 460800)


def list_ports() -> None:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print(f"{'PORT':<10} {'DESCRIPTION':<40} HWID")
    for p in ports:
        print(f"{p.device:<10} {(p.description or ''):<40} {p.hwid or ''}")


def hex_dump(data: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{hex_part:<{width * 3}}  {ascii_part}")
    return "\n".join(lines)


def run(port: str, baud: int, out_path: Path | None, line_width: int) -> None:
    print(f"Opening {port} @ {baud} baud (Ctrl+C to stop)...")
    try:
        ser = serial.Serial(port, baud, timeout=0.2)
    except serial.SerialException as exc:
        print(f"Could not open {port}: {exc}")
        return

    out_file = open(out_path, "wb") if out_path else None
    total_bytes = 0
    newline_count = 0
    sync_count = 0
    start = time.monotonic()
    last_report = start

    try:
        while True:
            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                total_bytes += len(chunk)
                newline_count += chunk.count(b"\n")
                sync_count += chunk.count(FRAME_SYNC)
                if out_file:
                    out_file.write(chunk)
                print(hex_dump(chunk, width=line_width))

            now = time.monotonic()
            if now - last_report >= 1.0:
                elapsed = now - start
                bytes_per_s = total_bytes / elapsed if elapsed else 0.0
                lines_per_s = newline_count / elapsed if elapsed else 0.0
                frames_per_s = sync_count / elapsed if elapsed else 0.0
                print(
                    f"-- {elapsed:6.1f}s | {total_bytes} bytes | {bytes_per_s:8.1f} B/s | "
                    f"CSV lines/s: {lines_per_s:6.1f} | binary frames/s: {frames_per_s:6.1f} --"
                )
                last_report = now
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        if out_file:
            out_file.close()
            print(f"\nCapture saved to {out_path}")
        elapsed = time.monotonic() - start
        rate = total_bytes / elapsed if elapsed else 0.0
        print(f"Total: {total_bytes} bytes in {elapsed:.1f}s ({rate:.1f} B/s estimated)")


def main() -> None:
    parser = argparse.ArgumentParser(description="CWXS serial protocol diagnostic tool")
    parser.add_argument("--list", action="store_true", help="List available serial ports and exit")
    parser.add_argument("--port", help="Serial port, e.g. COM7")
    parser.add_argument(
        "--baud", type=int, default=DEFAULT_BAUD_RATE, choices=SUPPORTED_BAUD_RATES
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="Path to save a raw binary capture, e.g. capture.bin"
    )
    parser.add_argument("--width", type=int, default=16, help="Bytes per hex dump line")
    args = parser.parse_args()

    if args.list or not args.port:
        list_ports()
        if not args.port:
            print("\nPass --port <COMx> to start capturing.")
        return

    run(args.port, args.baud, args.out, args.width)


if __name__ == "__main__":
    main()
