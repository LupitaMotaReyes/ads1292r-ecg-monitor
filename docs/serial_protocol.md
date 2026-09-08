# Serial Protocol

## The stock CWXS protocol is unknown

The protocol the CWXS PCB's stock firmware actually transmits over Bluetooth has
**not** been reverse engineered as part of this project. Do not assume it is CSV,
do not assume a particular baud rate, and do not assume any particular framing.

Before writing a parser for the stock firmware:

1. Connect the CWXS PCB (battery + Bluetooth) and its USB receiver to the PC.
2. Run `python tools/serial_inspector.py --list` to find the COM port.
3. Run `python tools/serial_inspector.py --port COMx --baud 115200 --out capture.bin`
   (try other baud rates from `SUPPORTED_BAUD_RATES` in `src/config.py` if the
   output looks like noise).
4. Study the hex dump / ASCII column / bytes-per-second / lines-per-second /
   frames-per-second counters to figure out the real framing.
5. Only once the real protocol is understood should a dedicated parser for it be
   added to `src/acquisition/protocol.py`.

## This project's own protocols

Two protocols are defined and implemented in `src/acquisition/protocol.py` (PC
side) and `firmware/cwxs_ads1292r_nano/protocol.h` (firmware side). They only
apply if you flash the alternative firmware in this repository onto the Nano —
they are **not** a claim about what the stock firmware sends.

### DEBUG MODE (CSV)

Human-readable ASCII, one sample per line:

```
timestamp,ecg,respiration,status
```

Example:

```
1250,-138422,5021,0
```

Parsed by `CSVProtocolParser`, which tolerates partial lines split across reads
and silently drops (while counting) malformed lines instead of crashing.

### STREAM MODE (binary)

A compact 14-byte frame, parsed by `BinaryStreamParser`:

| Offset | Size | Field                                   |
|--------|------|------------------------------------------|
| 0      | 2    | Sync header: `0xA5 0x5A`                  |
| 2      | 4    | Sample counter, `uint32`, little-endian   |
| 6      | 3    | ECG, 24-bit signed, little-endian         |
| 9      | 3    | Respiration, 24-bit signed, little-endian |
| 12     | 1    | Status flags                              |
| 13     | 1    | Checksum: XOR of bytes 0–12               |

The parser resynchronizes automatically on a checksum mismatch or lost sync byte:
it drops one byte at a time and rescans for `0xA5 0x5A` rather than desyncing
permanently on a single corrupted byte.

## Baud rate

`DEFAULT_BAUD_RATE = 115200` in `src/config.py` / `src/acquisition/protocol.py` is
a **testing default**, not a confirmed CWXS specification. The application exposes
`SUPPORTED_BAUD_RATES = (9600, 57600, 115200, 230400, 460800)` in Settings, and any
of them can be selected.

## Measuring the real sample rate

The kit is advertised at ~500 SPS, but the actual delivered rate should always be
measured, not assumed. `SampleRateEstimator` (in `src/acquisition/protocol.py`)
computes a real, sliding-window sample rate from however many samples were
actually parsed per unit of wall-clock time — use it instead of trusting the
configured `sample_rate_hz`.
