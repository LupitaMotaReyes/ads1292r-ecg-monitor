#include "ads1292r.h"

#include <SPI.h>

#include "ads1292r_registers.h"

namespace {
// SPI mode: ADS1292R samples MOSI on the SCLK rising edge with SCLK idling low
// (CPOL=0, CPHA=1) per the datasheet timing diagrams, i.e. SPI_MODE1.
constexpr uint32_t kSpiClockHz = 4000000;
const SPISettings kSpiSettings(kSpiClockHz, MSBFIRST, SPI_MODE1);

int32_t signExtend24(uint32_t value) {
  if (value & 0x800000UL) {
    value |= 0xFF000000UL;
  }
  return static_cast<int32_t>(value);
}
}  // namespace

void ADS1292R::begin(const ADS1292RPins &pins) {
  pins_ = pins;
  pinMode(pins_.pwdn_reset, OUTPUT);
  pinMode(pins_.start, OUTPUT);
  pinMode(pins_.drdy, INPUT);
  pinMode(pins_.cs, OUTPUT);

  digitalWrite(pins_.cs, HIGH);
  digitalWrite(pins_.start, LOW);
  digitalWrite(pins_.pwdn_reset, HIGH);

  SPI.begin();
}

void ADS1292R::selectChip() const { digitalWrite(pins_.cs, LOW); }
void ADS1292R::deselectChip() const { digitalWrite(pins_.cs, HIGH); }

void ADS1292R::resetDevice() {
  digitalWrite(pins_.pwdn_reset, LOW);
  delay(1);
  digitalWrite(pins_.pwdn_reset, HIGH);
  delay(1);

  sendCommand(ADS1292R_CMD_RESET);
  delay(10);
  // Leave RDATAC mode (if it was somehow active) so registers can be addressed.
  sendCommand(ADS1292R_CMD_SDATAC);
  delay(1);
}

void ADS1292R::sendCommand(uint8_t command) {
  SPI.beginTransaction(kSpiSettings);
  selectChip();
  SPI.transfer(command);
  deselectChip();
  SPI.endTransaction();
}

uint8_t ADS1292R::readRegister(uint8_t address) {
  SPI.beginTransaction(kSpiSettings);
  selectChip();
  SPI.transfer(ADS1292R_CMD_RREG | (address & 0x1F));
  SPI.transfer(0x00);  // read exactly 1 register: n - 1 = 0
  uint8_t value = SPI.transfer(0x00);
  deselectChip();
  SPI.endTransaction();
  return value;
}

void ADS1292R::writeRegister(uint8_t address, uint8_t value) {
  SPI.beginTransaction(kSpiSettings);
  selectChip();
  SPI.transfer(ADS1292R_CMD_WREG | (address & 0x1F));
  SPI.transfer(0x00);  // write exactly 1 register: n - 1 = 0
  SPI.transfer(value);
  deselectChip();
  SPI.endTransaction();
}

void ADS1292R::startConversions() {
  digitalWrite(pins_.start, HIGH);
  sendCommand(ADS1292R_CMD_RDATAC);
}

void ADS1292R::stopConversions() {
  sendCommand(ADS1292R_CMD_SDATAC);
  digitalWrite(pins_.start, LOW);
}

bool ADS1292R::isDataReady() const { return digitalRead(pins_.drdy) == LOW; }

void ADS1292R::readData(int32_t &ch1, int32_t &ch2, uint8_t &statusHigh) {
  SPI.beginTransaction(kSpiSettings);
  selectChip();

  // 3-byte status word, then two 24-bit channel words (RDATAC frame format).
  statusHigh = SPI.transfer(0x00);
  SPI.transfer(0x00);
  SPI.transfer(0x00);

  uint32_t rawCh1 = 0;
  rawCh1 = (rawCh1 << 8) | SPI.transfer(0x00);
  rawCh1 = (rawCh1 << 8) | SPI.transfer(0x00);
  rawCh1 = (rawCh1 << 8) | SPI.transfer(0x00);

  uint32_t rawCh2 = 0;
  rawCh2 = (rawCh2 << 8) | SPI.transfer(0x00);
  rawCh2 = (rawCh2 << 8) | SPI.transfer(0x00);
  rawCh2 = (rawCh2 << 8) | SPI.transfer(0x00);

  deselectChip();
  SPI.endTransaction();

  ch1 = signExtend24(rawCh1);
  ch2 = signExtend24(rawCh2);
}

bool ADS1292R::verifyDevice() {
  uint8_t id = readRegister(ADS1292R_REG_ID);
  return (id & ADS1292R_ID_UPPER_MASK) == ADS1292R_ID_UPPER_VAL;
}
