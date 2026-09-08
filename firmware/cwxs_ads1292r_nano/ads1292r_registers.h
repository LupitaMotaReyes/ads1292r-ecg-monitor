// ADS1292R register map and SPI op-codes.
//
// These addresses and command bytes come from the public Texas Instruments ADS1292R
// datasheet (SBAS502) and are generic to any ADS1292R, not specific to the CWXS
// module. They are safe to treat as fact. What is NOT confirmed is which values the
// CWXS PCB/firmware actually writes into these registers at runtime — see
// docs/ads1292r.md, "Hardware assumptions requiring verification".
#ifndef ADS1292R_REGISTERS_H
#define ADS1292R_REGISTERS_H

// -- Register addresses --------------------------------------------------------
#define ADS1292R_REG_ID         0x00
#define ADS1292R_REG_CONFIG1    0x01
#define ADS1292R_REG_CONFIG2    0x02
#define ADS1292R_REG_LOFF       0x03
#define ADS1292R_REG_CH1SET     0x04
#define ADS1292R_REG_CH2SET     0x05
#define ADS1292R_REG_RLD_SENS   0x06
#define ADS1292R_REG_LOFF_SENS  0x07
#define ADS1292R_REG_LOFF_STAT  0x08
#define ADS1292R_REG_RESP1      0x09
#define ADS1292R_REG_RESP2      0x0A
#define ADS1292R_REG_GPIO       0x0B

// -- SPI command op-codes (system commands) -------------------------------------
#define ADS1292R_CMD_WAKEUP  0x02
#define ADS1292R_CMD_STANDBY 0x04
#define ADS1292R_CMD_RESET   0x06
#define ADS1292R_CMD_START   0x08
#define ADS1292R_CMD_STOP    0x0A
#define ADS1292R_CMD_RDATAC  0x10
#define ADS1292R_CMD_SDATAC  0x11
#define ADS1292R_CMD_RDATA   0x12

// Register read/write op-codes are OR'd with the register address:
//   RREG:  0x20 | address, followed by (n-1)
//   WREG:  0x40 | address, followed by (n-1)
#define ADS1292R_CMD_RREG 0x20
#define ADS1292R_CMD_WREG 0x40

// Expected ID register value family for ADS129x parts (datasheet Table 14).
// The low nibble varies by exact part revision; only the upper bits are checked
// by ads1292r_verify_device() to avoid over-fitting to one silicon revision.
#define ADS1292R_ID_UPPER_MASK 0xE0
#define ADS1292R_ID_UPPER_VAL  0x80

#endif // ADS1292R_REGISTERS_H
