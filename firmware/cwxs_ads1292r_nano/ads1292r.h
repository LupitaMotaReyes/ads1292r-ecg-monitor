// Minimal ADS1292R driver over hardware SPI for the Arduino Nano (ATmega328P)
// mounted on the CWXS carrier PCB, talking to the CWXS purple ADS1292R module.
//
// Pin assignment (see docs/cwxs_hardware.md — confirmed only for this module's SPI
// wiring, NOT a claim about the rest of the CWXS PCB):
//   PWDN/RESET -> D4
//   START      -> D5
//   DRDY       -> D6
//   CS         -> D7
//   MOSI       -> D11 (hardware SPI)
//   MISO       -> D12 (hardware SPI)
//   SCLK       -> D13 (hardware SPI)
#ifndef ADS1292R_H
#define ADS1292R_H

#include <Arduino.h>

struct ADS1292RPins {
  uint8_t pwdn_reset;
  uint8_t start;
  uint8_t drdy;
  uint8_t cs;
};

class ADS1292R {
 public:
  void begin(const ADS1292RPins &pins);

  // Hardware reset sequence per datasheet timing requirements.
  void resetDevice();

  uint8_t readRegister(uint8_t address);
  void writeRegister(uint8_t address, uint8_t value);
  void sendCommand(uint8_t command);

  void startConversions();
  void stopConversions();

  // True once DRDY goes low, signalling a new sample is ready.
  bool isDataReady() const;

  // Reads one 3-byte status word + two 24-bit channel samples (9 bytes total),
  // per the ADS1292R RDATA frame format. Values are sign-extended to int32_t.
  void readData(int32_t &ch1, int32_t &ch2, uint8_t &statusHigh);

  // Reads the ID register and checks it against the known ADS129x family pattern.
  // Returns true if a device that looks like an ADS1292R responded.
  bool verifyDevice();

 private:
  ADS1292RPins pins_{};

  void selectChip() const;
  void deselectChip() const;
};

#endif // ADS1292R_H
