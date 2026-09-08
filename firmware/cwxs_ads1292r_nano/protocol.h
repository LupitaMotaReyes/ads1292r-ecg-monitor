// Wire protocols implemented by THIS alternative firmware.
//
// This is NOT the stock CWXS firmware's protocol, which has not been reverse
// engineered (see docs/serial_protocol.md and tools/serial_inspector.py). Only use
// this once you have deliberately chosen to flash your own firmware onto the Nano.
//
//   DEBUG_CSV     -> "timestamp,ecg,respiration,status\n" (ASCII, e.g. for a
//                     terminal or the CSVProtocolParser in src/acquisition/protocol.py)
//   STREAM_BINARY -> 14-byte binary frame matching BinaryStreamParser / FRAME_SYNC /
//                     FRAME_SIZE in src/acquisition/protocol.py
#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <Arduino.h>

#define PROTOCOL_FRAME_SYNC_0 0xA5
#define PROTOCOL_FRAME_SYNC_1 0x5A
#define PROTOCOL_FRAME_SIZE 14

inline void protocol_send_debug_csv(uint32_t timestampMs, int32_t ecg, int32_t resp,
                                     uint8_t status) {
  Serial.print(timestampMs);
  Serial.print(',');
  Serial.print(ecg);
  Serial.print(',');
  Serial.print(resp);
  Serial.print(',');
  Serial.println(status);
}

inline void protocol_send_stream_binary(uint32_t counter, int32_t ecg, int32_t resp,
                                         uint8_t status) {
  uint8_t frame[PROTOCOL_FRAME_SIZE];

  frame[0] = PROTOCOL_FRAME_SYNC_0;
  frame[1] = PROTOCOL_FRAME_SYNC_1;

  frame[2] = static_cast<uint8_t>(counter & 0xFF);
  frame[3] = static_cast<uint8_t>((counter >> 8) & 0xFF);
  frame[4] = static_cast<uint8_t>((counter >> 16) & 0xFF);
  frame[5] = static_cast<uint8_t>((counter >> 24) & 0xFF);

  uint32_t ecgU = static_cast<uint32_t>(ecg) & 0xFFFFFFUL;
  frame[6] = static_cast<uint8_t>(ecgU & 0xFF);
  frame[7] = static_cast<uint8_t>((ecgU >> 8) & 0xFF);
  frame[8] = static_cast<uint8_t>((ecgU >> 16) & 0xFF);

  uint32_t respU = static_cast<uint32_t>(resp) & 0xFFFFFFUL;
  frame[9] = static_cast<uint8_t>(respU & 0xFF);
  frame[10] = static_cast<uint8_t>((respU >> 8) & 0xFF);
  frame[11] = static_cast<uint8_t>((respU >> 16) & 0xFF);

  frame[12] = status;

  uint8_t checksum = 0;
  for (uint8_t i = 0; i < PROTOCOL_FRAME_SIZE - 1; i++) {
    checksum ^= frame[i];
  }
  frame[13] = checksum;

  Serial.write(frame, PROTOCOL_FRAME_SIZE);
}

#endif  // PROTOCOL_H
