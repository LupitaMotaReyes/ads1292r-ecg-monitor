# CWXS ADS1292R Nano/Uno Firmware (optional, alternative)

This is an **optional** replacement firmware for the Arduino on the CWXS carrier
PCB. It is provided for the case where you eventually need full control over the
ADS1292R configuration and wire protocol — for example, if the stock CWXS
firmware/PCB routing turns out not to work or can't be reused.

## Read this first

**Do not flash this before listening to what the stock CWXS firmware already
transmits.** The kit ships as a working system (ADS1292R -> Nano -> Bluetooth ->
USB receiver) with its own firmware already on the Nano. Use
`python tools/serial_inspector.py` from the repository root to capture and study
the real Bluetooth traffic first. Only flash this sketch if you decide the stock
firmware's protocol cannot be reused as-is.

## Hardware — confirmed working configuration

This exact pin mapping and register sequence were verified on real hardware: an
Arduino Nano **and** a separate Arduino Uno, each wired directly to the CWXS
purple ADS1292R module with jumper wires (bypassing the CWXS carrier PCB, whose
internal routing between its own Nano socket and the ADS1292R module is still
`TO BE VERIFIED ON HARDWARE` — this only confirms the module's own SPI wiring).

| Signal        | Nano/Uno pin |
|---------------|--------------|
| PWDN / RESET  | D4           |
| START         | D5           |
| DRDY          | D6           |
| CS            | D7           |
| MOSI          | D11          |
| MISO          | D12          |
| SCLK          | D13          |
| 5V            | 5V           |
| GND           | GND          |

**Two things that looked fine but silently broke detection before this was
verified working:**

- **SPI clock speed.** The datasheet allows up to ~4 MHz, but that is too fast for
  a breadboard/jumper-wire connection — every register read came back `0x00`
  (not garbage, a clean zero) until the clock was slowed to **500 kHz**
  (`SPISettings` in the `.ino`). If you see the same all-zero ID register on your
  own wiring, try this first.
- **Missing register configuration.** Reading the ID register alone doesn't need
  channel configuration, but getting real ECG samples out does. `setup()` writes
  `CONFIG1`, `CONFIG2`, `CH1SET`, `CH2SET`, `RLD_SENS`, `LOFF_SENS`, `RESP1` and
  `RESP2` before starting conversions — skipping these leaves the front end
  unconfigured even if the ID check passes.

## Files

- `cwxs_ads1292r_nano.ino` — everything: pin setup, SPI driver, ADS1292R register
  configuration, and the acquisition loop.
- `protocol.h` — this project's own wire formats (DEBUG CSV and STREAM binary),
  matching `src/acquisition/protocol.py` on the PC side. The firmware sends raw,
  unfiltered ADC counts — all filtering happens on the PC side
  (`src/signal_processing/`), which already has a tested filter chain and expects
  raw counts, not pre-filtered values.

## Startup diagnostic

On boot the sketch resets the ADS1292R, configures it, reads the ID register over
SPI, and prints it: `ID register = 0x..`.

This is informational only — it does **not** gate whether the sketch starts
streaming. An earlier version of this firmware refused to stream unless the ID
matched the genuine-TI-part bit pattern (`0x80` under mask `0xE0`), which turned
out to be the wrong call: on this kit's module, the ID register reads back
**`0x73`** (confirmed on real hardware) — it does not match that pattern, yet
the chip responds correctly to every command and produces real, live ECG data.
This is almost certainly a rebadged/clone front-end chip or a different silicon
revision, not a wiring problem — checking the ID strictly meant tearing right
past a working sensor. All `readRegister`/`writeRegister` calls returning
**exactly `0x00`** on *every* register (not just ID) is still a much stronger
sign of a real problem — SPI clock too fast for the wiring, CS/SCK/MISO/MOSI
miswired, or no power reaching the module — than a single register reading an
unexpected-but-nonzero value.

## Protocol modes

Set `PROTOCOL_MODE` at the top of the `.ino` file:

- `PROTOCOL_MODE_DEBUG_CSV` (default) — human-readable ASCII lines
  `timestamp,ch1,ch2,status`, easy to read in a terminal.
- `PROTOCOL_MODE_STREAM_BINARY` — compact 14-byte binary frames for higher
  throughput, parsed on the PC by `BinaryStreamParser`.

## Build

This project builds with PlatformIO (`platformio.ini` in this folder defines both
a `nanoatmega328new` and a `uno` environment):

```powershell
pio run -e uno --target upload --upload-port COMx
# or
pio run -e nanoatmega328new --target upload --upload-port COMx
```

Arduino IDE (or arduino-cli) works too:

- Board: **Arduino Nano** or **Arduino Uno**
- Processor (Nano only): **ATmega328P** (try "Old Bootloader" first if the classic
  Nano fails to upload — this varies by clone/bootloader revision)
- Baud rate for upload: whatever your USB-serial adapter needs, independent of
  `kBaudRate` used for the running sketch's `Serial.begin()`

## Known unverified assumptions

- CH2 here is a second ECG-style electrode channel (gain x12, normal input),
  **not** true respiration data — the ADS1292R's respiration AC-excitation feature
  is left disabled (`RESP1`/`RESP2` at their reset-ish values). If you enable
  `respiration_channel` in the app's Settings, you'll see CH2's raw waveform, but
  it will not be a real breathing-rate signal until respiration excitation is
  actually configured.
- Which physical channel (1 or 2) is wired to which electrode pair is
  `TO BE VERIFIED ON HARDWARE` for your specific module.
- `kBaudRate = 115200` is only a testing default (`DEFAULT_BAUD_RATE` in
  `src/acquisition/protocol.py`), not a confirmed CWXS specification.
