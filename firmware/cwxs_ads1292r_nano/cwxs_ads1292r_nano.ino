// CWXS ADS1292R Nano/Uno firmware — OPTIONAL alternative to the kit's stock firmware.
//
// IMPORTANT: do not flash this before first listening to what the stock CWXS PCB
// already transmits over its Bluetooth link (see tools/serial_inspector.py at the
// repository root). This sketch only matters if you deliberately decide to replace
// the original firmware with your own.
//
// Hardware: Arduino Nano or Uno (ATmega328P), wired directly by SPI to the CWXS
// purple ADS1292R module (bypassing the CWXS carrier PCB, whose internal routing
// is not known — see docs/cwxs_hardware.md). Pin mapping and register sequence
// below are CONFIRMED WORKING on real hardware wired this way — see
// docs/ads1292r.md for the pinout table and firmware/cwxs_ads1292r_nano/README.md
// for the story of what didn't work before this (mainly: the SPI clock has to be
// slow enough for jumper wires — 500 kHz here, not the 4 MHz first tried).

#include <SPI.h>

#include "protocol.h"

#define PROTOCOL_MODE_DEBUG_CSV 0
#define PROTOCOL_MODE_STREAM_BINARY 1
// Switch to PROTOCOL_MODE_STREAM_BINARY once the CSV path is confirmed working.
#define PROTOCOL_MODE PROTOCOL_MODE_DEBUG_CSV

// -- Pin assignment (see docs/ads1292r.md) --------------------------------------
#define PIN_PWDN 4
#define PIN_START 5
#define PIN_DRDY 6
#define PIN_CS 7
// MOSI = D11, MISO = D12, SCK = D13 — the ATmega328P's fixed hardware SPI pins.

// -- ADS1292R commands -----------------------------------------------------------
#define CMD_RESET 0x06
#define CMD_SDATAC 0x11
#define CMD_RDATA 0x12

// -- ADS1292R registers ------------------------------------------------------------
#define REG_ID 0x00
#define REG_CONFIG1 0x01
#define REG_CONFIG2 0x02
#define REG_LOFF 0x03
#define REG_CH1SET 0x04
#define REG_CH2SET 0x05
#define REG_RLD_SENS 0x06
#define REG_LOFF_SENS 0x07
#define REG_RESP1 0x09
#define REG_RESP2 0x0A

// UNVERIFIED: a value chosen for testing this firmware, not a confirmed CWXS spec.
constexpr uint32_t kBaudRate = 115200;

// ADS1292R samples MOSI on the SCLK rising edge with SCLK idling low (CPOL=0,
// CPHA=1), i.e. SPI_MODE1 — per datasheet timing diagrams. 500 kHz (not the
// datasheet's max ~4 MHz) is what reliably works over jumper wires; a faster
// clock read back nothing but 0x00 on this exact hardware.
const SPISettings kAdsSpi(500000, MSBFIRST, SPI_MODE1);

uint32_t sampleCounter = 0;

void sendCommand(uint8_t command) {
  SPI.beginTransaction(kAdsSpi);
  digitalWrite(PIN_CS, LOW);
  delayMicroseconds(5);
  SPI.transfer(command);
  delayMicroseconds(10);
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();
  delayMicroseconds(20);
}

void writeRegister(uint8_t address, uint8_t value) {
  SPI.beginTransaction(kAdsSpi);
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(0x40 | (address & 0x1F));  // WREG
  delayMicroseconds(10);
  SPI.transfer(0x00);  // n - 1 = 0: exactly one register
  delayMicroseconds(10);
  SPI.transfer(value);
  delayMicroseconds(10);
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();
}

uint8_t readRegister(uint8_t address) {
  SPI.beginTransaction(kAdsSpi);
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(0x20 | (address & 0x1F));  // RREG
  delayMicroseconds(10);
  SPI.transfer(0x00);  // n - 1 = 0: exactly one register
  delayMicroseconds(10);
  uint8_t value = SPI.transfer(0x00);
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();
  return value;
}

int32_t signExtend24(uint8_t b1, uint8_t b2, uint8_t b3) {
  int32_t value = (static_cast<int32_t>(b1) << 16) | (static_cast<int32_t>(b2) << 8) | b3;
  if (value & 0x800000) {
    value |= 0xFF000000;
  }
  return value;
}

// Reads one RDATA frame: 3-byte status word + two 24-bit channel samples.
void readAds(int32_t &ch1, int32_t &ch2) {
  uint8_t data[9];

  SPI.beginTransaction(kAdsSpi);
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(CMD_RDATA);
  delayMicroseconds(10);
  for (uint8_t i = 0; i < 9; i++) {
    data[i] = SPI.transfer(0x00);
  }
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();

  ch1 = signExtend24(data[3], data[4], data[5]);
  ch2 = signExtend24(data[6], data[7], data[8]);
}

void setup() {
  Serial.begin(kBaudRate);
  delay(1000);

  pinMode(PIN_CS, OUTPUT);
  pinMode(PIN_PWDN, OUTPUT);
  pinMode(PIN_START, OUTPUT);
  pinMode(PIN_DRDY, INPUT);
  pinMode(10, OUTPUT);  // hardware SS must stay an output for SPI master mode
  digitalWrite(10, HIGH);
  digitalWrite(PIN_CS, HIGH);
  digitalWrite(PIN_START, LOW);

  // Hardware reset pulse per datasheet timing requirements.
  digitalWrite(PIN_PWDN, LOW);
  delay(100);
  digitalWrite(PIN_PWDN, HIGH);
  delay(500);

  SPI.begin();
  delay(50);

  sendCommand(CMD_RESET);
  delay(100);
  sendCommand(CMD_SDATAC);  // leave RDATAC mode so registers can be addressed
  delay(20);

  // -- Channel/reference configuration (confirmed working on real hardware) ------
  writeRegister(REG_CONFIG1, 0x01);    // continuous conversion, 250 SPS
  writeRegister(REG_CONFIG2, 0xA0);    // internal reference enabled, VREF = 2.42V
  writeRegister(REG_LOFF, 0x10);
  writeRegister(REG_CH1SET, 0x60);     // channel on, gain x12, normal electrode input
  writeRegister(REG_CH2SET, 0x60);     // channel on, gain x12, normal electrode input
  // RLD buffer on, both channels' electrodes feed the right-leg-drive reference —
  // we don't yet know which physical channel is ECG vs. respiration on this module.
  writeRegister(REG_RLD_SENS, 0x2F);
  writeRegister(REG_LOFF_SENS, 0x00);  // lead-off detection disabled
  writeRegister(REG_RESP1, 0x02);
  writeRegister(REG_RESP2, 0x03);

  // Informational only — printed, never used to gate streaming. The expected
  // upper-bit pattern for a genuine TI part is 0x80 under mask 0xE0, but cheap
  // clone/rebadged chips on kits like this one may report a different ID while
  // still working perfectly over SPI, so the previous version of this firmware
  // (which refused to stream unless the ID matched that mask) silently blocked
  // real, working data — this print is just for your own reference.
  Serial.print(F("ID register = 0x"));
  Serial.println(readRegister(REG_ID), HEX);

  digitalWrite(PIN_START, HIGH);
  delay(100);
}

void loop() {
  if (digitalRead(PIN_DRDY) != LOW) {
    return;
  }

  int32_t ch1 = 0;
  int32_t ch2 = 0;
  readAds(ch1, ch2);

  uint32_t timestampMs = millis();

#if PROTOCOL_MODE == PROTOCOL_MODE_DEBUG_CSV
  protocol_send_debug_csv(timestampMs, ch1, ch2, 0);
#else
  protocol_send_stream_binary(sampleCounter, ch1, ch2, 0);
#endif

  sampleCounter++;

  // Avoid reading the same sample twice before DRDY pulses again.
  while (digitalRead(PIN_DRDY) == LOW) {
  }
}
