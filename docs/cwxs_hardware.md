# CWXS Hardware

This project targets a specific commercial kit, not a from-scratch ADS1292R
breadboard build:

**CWXS ADS1292R-Arduino Wireless Transmission Kit**

The physical system is:

```
PC (Windows)
   |
   v
CWXS USB Bluetooth receiver
   |
   | wireless (Bluetooth)
   v
Bluetooth module on the CWXS PCB
   |
   v
Arduino Nano (ATmega328P)
   |
   | SPI
   v
CWXS purple ADS1292R module
   |
   v
Electrode cable -> ECG electrodes
```

## CWXS ADS1292R-Arduino Kit

### PCB base

A CWXS-branded carrier PCB that provides, in one board:

- a socket/header set for an Arduino Nano;
- power management from a 3.7 V LiPo battery;
- a physical power switch;
- an integrated/connected Bluetooth module for wireless transmission;
- connections to the purple ADS1292R module.

This project does **not** design a new PCB and does **not** replace the CWXS PCB —
it is built to work with the existing board as-is.

### Arduino

An Arduino Nano, ATmega328P, mounted directly on the CWXS carrier PCB.

### ADS1292R Module

A purple PCB module built around the Texas Instruments ADS1292R analog front-end,
connected to the Nano over SPI. See [`ads1292r.md`](ads1292r.md) for the register
map and pin assignment used by this project.

### Wireless Receiver

The USB Bluetooth receiver dongle included with the kit, plugged into the Windows
PC. It should enumerate as a COM port (or equivalent serial device) in Windows —
see [`serial_protocol.md`](serial_protocol.md) for how the application discovers
and uses it.

## System diagram

```
Electrodes
    |
    v
+-----------------+
| ADS1292R Module |
|   Purple PCB    |
+--------+--------+
         | SPI
         v
+-----------------+
|  Arduino Nano   |
|   ATmega328P    |
+--------+--------+
         |
         v
+-----------------+
|    CWXS PCB     |
| LiPo + Bluetooth|
+--------+--------+
         |
      Bluetooth
         |
         v
+-----------------+
| CWXS USB Dongle |
+--------+--------+
         | USB
         v
+-----------------+
|   Windows PC    |
|   ECG Monitor   |
+-----------------+
```

## Hardware assumptions requiring verification

The following are **not** confirmed facts about this specific CWXS PCB/firmware.
They must never be treated as ground truth until measured or verified against the
real hardware — use `tools/serial_inspector.py` and a logic analyzer/multimeter
where applicable:

- exact baud rate used by the CWXS Bluetooth link;
- exact format of the packets the stock CWXS firmware transmits over Bluetooth;
- which Nano UART pins the Bluetooth module is actually wired to (assumed to *not*
  necessarily be D0/D1, since the module could be soft-wired or share the same
  hardware UART used for USB programming — `TO BE VERIFIED ON HARDWARE`);
- exact PCB revision and any differences in charging/power circuitry between
  revisions;
- PGA gain actually configured in the ADS1292R by the stock firmware;
- VREF actually used by the ADS1292R (internal vs. external reference);
- full ADS1292R register configuration used by the stock firmware
  (`CONFIG1`, `CONFIG2`, `CHxSET`, `RESP1`, `RESP2`, etc.);
- exact interpretation of the 24-bit sample format used by the stock firmware
  (this project's own protocol, defined in `src/acquisition/protocol.py`, is a
  distinct, self-designed format for use with the alternative firmware only);
- which ADS1292R channel is wired to the ECG electrodes vs. respiration sensing
  in the stock firmware.

## Safety

This project is intended for education, research, prototyping and engineering
development. It is not a certified medical device and must not be used for
diagnosis or clinical decision-making.

When acquiring signals from a person:

- power the PCB from its LiPo battery only, and use the Bluetooth link — never
  create an unnecessary direct electrical connection between electrodes and
  mains-powered equipment;
- the CWXS USB Bluetooth receiver can safely stay plugged into the PC, since the
  link between it and the PCB is wireless;
- do not modify the hardware without considering electrical isolation and the
  general safety practices used for electromedical equipment.
