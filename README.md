# CWXS ADS1292R ECG Monitor

**Real-time ECG acquisition and visualization using the CWXS ADS1292R-Arduino wireless board**

> This project is intended for education, research, prototyping and engineering
> development. It is not a certified medical device and must not be used for
> diagnosis or clinical decision-making.

## Features

- Real-time ECG plot (pyqtgraph, scrolling 5–10 s buffer, pan/zoom/autoscale, grid).
- Acquisition rate (e.g. 500 SPS) fully decoupled from the GUI redraw rate.
- Heart rate (BPM) from an adaptive R-peak detector with a refractory period and
  RR-interval plausibility rejection — never a fabricated number.
- Heuristic (non-clinical) signal-quality indicator: GOOD / FAIR / POOR.
- Raw ADC counts, µV or mV display, with a documented ADC-counts-to-volts
  conversion that requires an explicit VREF/PGA gain rather than guessing them.
- CSV + JSON-metadata recording.
- `tools/serial_inspector.py`: a standalone diagnostic to capture and study
  whatever the CWXS Bluetooth receiver actually transmits, in hex/ASCII, with
  throughput measurement and raw binary capture — **use this before assuming any
  protocol** about the stock CWXS firmware.

## Hardware

This project targets a specific commercial kit:
**CWXS ADS1292R-Arduino Wireless Transmission Kit** — not a from-scratch
ADS1292R breadboard build. Full details, diagrams and unverified assumptions are
in [`docs/cwxs_hardware.md`](docs/cwxs_hardware.md).

```
Electrodes -> ADS1292R module (purple, SPI) -> Arduino Nano -> CWXS PCB
(LiPo + Bluetooth) -> CWXS USB Bluetooth receiver -> Windows PC
```

### CWXS PCB

The CWXS carrier PCB provides the Arduino Nano socket, LiPo (3.7 V) power
management, the power switch, and the Bluetooth module/transmission. **This
project does not design a new PCB** — it is built to work with the existing
CWXS board.

### ADS1292R Module

The purple CWXS module built around the TI ADS1292R, wired by SPI to the Nano.
Register map, pinout and the ADC-counts-to-volts formula are documented in
[`docs/ads1292r.md`](docs/ads1292r.md).

### Arduino Nano

A classic Arduino Nano (ATmega328P) mounted directly on the CWXS PCB. An
optional, alternative firmware for it lives in
[`firmware/cwxs_ads1292r_nano/`](firmware/cwxs_ads1292r_nano/) — see that
folder's README before flashing anything.

### Bluetooth USB Receiver

The USB Bluetooth dongle included with the kit, plugged into the PC. It should
enumerate as a Windows COM port; the application lists, auto-guesses and lets
you manually pick among available ports.

## Installation

Requires Python 3.12+.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

The application talks directly to the CWXS ADS1292R hardware — there is no
simulated/no-hardware mode. A receiver must be connected before you can Connect
and Start.

## Real Hardware Mode

1. Connect the 3.7 V LiPo battery to the CWXS PCB and power it on.
2. Plug the CWXS USB Bluetooth receiver into the PC and wait for Windows to
   create its COM port.
3. Launch the application.
4. Settings > Connection: select the COM port and baud rate (`115200` is only a
   testing default, not a confirmed CWXS specification — see
   [`docs/serial_protocol.md`](docs/serial_protocol.md)).
5. Click **Connect**, then **Start**.
6. Watch the ECG trace, heart rate and signal quality; use **Record** to save a
   CSV + metadata pair, **Stop** to end acquisition.

**Before assuming the stock firmware speaks any particular protocol, use
`tools/serial_inspector.py` to capture and study the real traffic first** — see
[Serial Inspector](#serial-inspector) below and
[`docs/serial_protocol.md`](docs/serial_protocol.md).

## Pinout

| ADS1292R signal | Arduino Nano pin |
|------------------|-------------------|
| PWDN / RESET     | D4                |
| START            | D5                |
| DRDY             | D6                |
| CS               | D7                |
| DIN / MOSI       | D11               |
| DOUT / MISO      | D12               |
| SCLK             | D13               |
| GND              | GND               |

Full register map and driver details: [`docs/ads1292r.md`](docs/ads1292r.md).

## Serial Inspector

```powershell
python tools/serial_inspector.py --list
python tools/serial_inspector.py --port COM7 --baud 115200
python tools/serial_inspector.py --port COM7 --baud 115200 --out capture.bin
```

Prints a live hex/ASCII dump of everything received, reports bytes/s, CSV
lines/s and binary-frame/s, and can save a raw `.bin` capture for offline
analysis. This is the intended first step for reverse-engineering the stock
CWXS protocol — see [`docs/serial_protocol.md`](docs/serial_protocol.md).

## Recording

Pressing **Record** creates, under `data/recordings/`:

- `ECG_YYYY-MM-DD_HH-MM-SS.csv` — columns: `timestamp, sample_index, ecg_raw,
  ecg_filtered, resp_raw, heart_rate, signal_quality`.
- `ECG_YYYY-MM-DD_HH-MM-SS_metadata.json` — hardware description, sample rate,
  baud rate, COM port, ADS1292R config (gain/VREF/channels), filter settings,
  duration and software version.

## Signal Processing

- `src/signal_processing/filters.py` — optional, streaming DC removal,
  high-pass, low-pass, 50/60 Hz notch (persistent filter state across chunks).
- `src/signal_processing/ecg_processing.py` — applies the configured filter
  chain while always preserving the raw signal, plus a heuristic (documented as
  non-clinical) signal-quality estimate.
- `src/signal_processing/heart_rate.py` — Pan-Tompkins-inspired R-peak
  detector with a refractory period, adaptive threshold, RR-interval
  plausibility rejection and BPM smoothing.
- `src/signal_processing/respiration_processing.py` — bandpass filtering and
  breathing-rate estimation for the ADS1292R respiration channel, when present.
- `src/signal_processing/units.py` — documented ADC-counts-to-volts conversion;
  requires an explicit, user-confirmed VREF and PGA gain.

## Troubleshooting

- **No serial ports listed**: confirm the CWXS USB receiver is plugged in and
  Windows created a COM port (Device Manager); try a different USB port.
- **Garbage/noise in Serial Inspector**: try other baud rates from
  `SUPPORTED_BAUD_RATES`; the real CWXS baud rate is not confirmed.
- **`ADS1292R NOT FOUND` from the alternative firmware**: SPI wiring/module
  problem, unrelated to Bluetooth — check the pinout table above.
- **Connection drops during acquisition**: `SerialManager` detects the failure,
  emits a disconnect, and (unless you explicitly disconnected) retries after a
  short delay; you can also reconnect manually.
- **BPM shows `-- BPM`**: not enough plausible R-peaks detected yet — check
  signal quality and electrode contact; the app never shows a fabricated value.

## Safety

See [`docs/cwxs_hardware.md`](docs/cwxs_hardware.md#safety). In short: power the
PCB from its LiPo battery and use the Bluetooth link for any acquisition on a
person; the USB Bluetooth receiver can safely stay connected to the PC since
that link is wireless; do not modify the hardware without considering
electrical isolation and standard electromedical safety practice.

## Development priorities (recommended order)

1. COM port detection + Serial Inspector + raw capture from the real CWXS
   receiver.
2. Reverse-engineer the stock CWXS protocol; add a parser for it.
3. Visualize real ECG from the CWXS PCB.
4. Filters, R-peaks, BPM and respiration on real data; recording.
5. Alternative Nano firmware — only if actually needed.

**Fundamental rule: do not replace the stock firmware before first listening to
what the CWXS PCB already transmits.**

## Project layout

```
cwxs-ads1292r-ecg-monitor/
├── firmware/cwxs_ads1292r_nano/   optional alternative Arduino firmware
├── src/
│   ├── main.py
│   ├── config.py
│   ├── ui/                        main window, plots, status panel, settings
│   ├── acquisition/                serial I/O, protocol parsers, circular buffer
│   ├── signal_processing/          filters, ECG/heart-rate/respiration, units
│   └── recording/                  CSV + metadata recorder
├── tools/serial_inspector.py       raw serial protocol diagnostic
├── tests/                          pytest suite
├── docs/                           hardware, ADS1292R, serial protocol docs
└── data/recordings/                recorded CSV + metadata output
```

## Testing

```powershell
pip install -r requirements.txt
pytest
ruff check .
```

## License

MIT — see [`LICENSE`](LICENSE).
