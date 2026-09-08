// CWXS ADS1292R Nano firmware — OPTIONAL alternative to the kit's stock firmware.
//
// IMPORTANT: do not flash this before first listening to what the stock CWXS PCB
// already transmits over its Bluetooth link (see tools/serial_inspector.py at the
// repository root). This sketch only matters if you deliberately decide to replace
// the original firmware with your own.
//
// Hardware: Arduino Nano (ATmega328P) mounted on the CWXS carrier PCB, wired by SPI
// to the CWXS purple ADS1292R module. See ads1292r.h for the pin mapping and
// docs/cwxs_hardware.md for the full system diagram.

#include <SPI.h>

#include "ads1292r.h"
#include "protocol.h"

#define PROTOCOL_MODE_DEBUG_CSV 0
#define PROTOCOL_MODE_STREAM_BINARY 1
// Switch to PROTOCOL_MODE_STREAM_BINARY once the CSV path is confirmed working.
#define PROTOCOL_MODE PROTOCOL_MODE_DEBUG_CSV

// Pin assignment from docs/cwxs_hardware.md / the project's ADS1292R pinout table.
constexpr ADS1292RPins kPins = {
    /* pwdn_reset */ 4,
    /* start      */ 5,
    /* drdy       */ 6,
    /* cs         */ 7,
};

// UNVERIFIED: a value chosen for testing this firmware, not a confirmed CWXS spec.
constexpr uint32_t kBaudRate = 115200;

// This firmware assumes ECG is wired to ADS1292R channel 1 and respiration to
// channel 2. TO BE VERIFIED ON HARDWARE against the actual electrode wiring.
ADS1292R ads;
uint32_t sampleCounter = 0;
bool deviceDetected = false;

void setup() {
  Serial.begin(kBaudRate);
  delay(200);

  ads.begin(kPins);
  ads.resetDevice();

  deviceDetected = ads.verifyDevice();
  Serial.println(deviceDetected ? F("ADS1292R detected") : F("ADS1292R NOT FOUND"));

  if (deviceDetected) {
    ads.startConversions();
  }
}

void loop() {
  if (!deviceDetected) {
    // Do not attempt to stream data from a device that never responded on SPI;
    // this is what lets DEBUG output distinguish a Bluetooth problem (no data at
    // all reaches the PC) from a SPI/wiring problem (this message never appears).
    return;
  }

  if (!ads.isDataReady()) {
    return;
  }

  int32_t ecg = 0;
  int32_t resp = 0;
  uint8_t status = 0;
  ads.readData(ecg, resp, status);

  uint32_t timestampMs = millis();

#if PROTOCOL_MODE == PROTOCOL_MODE_DEBUG_CSV
  protocol_send_debug_csv(timestampMs, ecg, resp, status);
#else
  protocol_send_stream_binary(sampleCounter, ecg, resp, status);
#endif

  sampleCounter++;
}
