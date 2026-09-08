# CWXS ADS1292R Nano Firmware (optional, alternative)

This is an **optional** replacement firmware for the Arduino Nano on the CWXS
carrier PCB. It is provided for the case where you eventually need full control
over the ADS1292R configuration and wire protocol.

## Read this first

**Do not flash this before listening to what the stock CWXS firmware already
transmits.** The kit ships as a working system (ADS1292R -> Nano -> Bluetooth ->
USB receiver) with its own firmware already on the Nano. Use
`python tools/serial_inspector.py` from the repository root to capture and study
the real Bluetooth traffic first. Only flash this sketch if you decide the stock
firmware's protocol cannot be reused as-is.

## Hardware assumed

- Arduino Nano, ATmega328P, mounted on the CWXS carrier PCB.
- CWXS purple ADS1292R module, connected to the Nano over SPI.
- Pin mapping (see `ads1292r.h`):

  | Signal        | Nano pin |
  |---------------|----------|
  | PWDN / RESET  | D4       |
  | START         | D5       |
  | DRDY          | D6       |
  | CS            | D7       |
  | MOSI          | D11      |
  | MISO          | D12      |
  | SCLK          | D13      |
  | GND           | GND      |

  This mapping is the project's working reference for the ADS1292R module's SPI
  wiring; the rest of the CWXS PCB's internal routing is `TO BE VERIFIED ON HARDWARE`.

## Files

- `cwxs_ads1292r_nano.ino` — sketch entry point: setup/verify/stream loop.
- `ads1292r.h` / `ads1292r.cpp` — ADS1292R SPI driver (register read/write, commands,
  reset, data read, device verification).
- `ads1292r_registers.h` — register addresses and SPI op-codes from the public TI
  ADS1292R datasheet.
- `protocol.h` — this project's own wire formats (DEBUG CSV and STREAM binary),
  matching `src/acquisition/protocol.py` on the PC side.

## Startup diagnostic

On boot the sketch resets the ADS1292R, reads the ID register over SPI, and prints
exactly one of:

```
ADS1292R detected
ADS1292R NOT FOUND
```

If you see `ADS1292R NOT FOUND`, the problem is in the SPI wiring/module, not the
Bluetooth link — no further data will be streamed until this passes. If you see
nothing at all on the PC side despite the Nano running, the problem is more likely
Bluetooth/pairing/COM-port related instead.

## Protocol modes

Set `PROTOCOL_MODE` at the top of the `.ino` file:

- `PROTOCOL_MODE_DEBUG_CSV` (default) — human-readable ASCII lines
  `timestamp,ecg,respiration,status`, easy to read in the Arduino Serial Monitor.
- `PROTOCOL_MODE_STREAM_BINARY` — compact 14-byte binary frames for higher
  throughput, parsed on the PC by `BinaryStreamParser`.

## Build

Arduino IDE (or arduino-cli) settings:

- Board: **Arduino Nano**
- Processor: **ATmega328P** (try "Old Bootloader" first if the classic Nano fails
  to upload — this varies by clone/bootloader revision)
- Baud rate for upload: whatever your USB-serial adapter needs, independent of
  `kBaudRate` used for the running sketch's `Serial.begin()`

## Known unverified assumptions

- This firmware assumes ECG is wired to ADS1292R channel 1 and respiration to
  channel 2 — `TO BE VERIFIED ON HARDWARE`.
- `kBaudRate = 115200` is only a testing default (`DEFAULT_BAUD_RATE` in
  `src/acquisition/protocol.py`), not a confirmed CWXS specification.
- ADS1292R register configuration (PGA gain, reference selection, etc.) is left at
  power-on-reset defaults in this minimal driver; tune `CONFIG1`/`CONFIG2`/`CHxSET`
  via `writeRegister()` once your gain/reference requirements are confirmed.
