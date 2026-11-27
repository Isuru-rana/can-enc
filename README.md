# can-enc: Anti-Theft Security for Vehicle CAN Bus

A low-cost hardware testbed for securing in-vehicle CAN traffic against theft attacks.
Three emulated vehicle modules share a group key and exchange encrypted commands over SAE J1939.

Originally built as a BEng final-year project (LJMU), "Robust Anti-Theft System for Vehicles to Counteract CAN Attacks".
Tag `v1.0-fyp` is the system exactly as submitted, apart from personal data removed from the code.

## System overview

```
 PC (Python host)        PC (Python host)        PC (Python host)
 key exchange, AES       key exchange, AES       key exchange, AES
       | USB-UART              | USB-UART              | USB-UART
   ESP32 + MCP2515         ESP32 + MCP2515         ESP32 + MCP2515        ESP32 + MCP2515
   IMM  (0x32)             KLE  (0x42)             CLM  (0x52)            sniffer (0x72)
       |                       |                       |                      |
 ======+=======================+=======================+======================+====  CAN 500 kbit/s
```

| Node | Address | Role |
|------|---------|------|
| IMM | 0x32 | Immobiliser: ignition (LED) |
| KLE | 0x42 | Keyless entry + alarm: SIM900A GSM, SMS alerts |
| CLM | 0x52 | Central locking: door LEDs |
| sniffer | 0x72 | Bus logger and test tool |

Alerts are also published over MQTT, for display in Home Assistant.

## Hardware

- ESP32-WROOM-32 dev board per node
- MCP2515 CAN module (8 MHz crystal), SPI at 10 MHz
- TXS0108E level shifter (3.3 V ESP32 to 5 V CAN module)
- Twisted-pair bus, 120 Ω termination at both ends
- SIM900A GSM module on the KLE node

ESP32 pins (all nodes): MISO 19, MOSI 23, SCK 18, CS 5, INT 21.

## Repository layout

| Folder | Contents |
|--------|----------|
| `firmware/j1939-{imm,kle,clm,sniff}/` | ESP-IDF projects, one per node |
| `firmware/*/components/j1939/` | Custom J1939-21 data-link layer (single frame, TP.CM_BAM, TP.DT, reassembly) |
| `firmware/*/components/mcp2515/` | MCP2515 SPI driver |
| `host/{imm,kle,clm}/` | Python application layer: group key exchange, AES encryption, message counters, GUI |
| `host/*/test_scripts/` | Latency test harness, plotting, and raw results (`results/*.csv`) |
| `tests/` | J1939 multi-frame and maximum-size transfer tests |
| `docs/fyp-report.pdf` | Final project report (May 2025): design, methodology, results |

## How it works (v1)

1. **Group key exchange.** The three host programs run a ring-based Diffie–Hellman group key exchange over the bus.
   The shared value is hashed with SHA-256; the first 16 bytes become the AES-128 key. Keys are rotated after a set number of messages.
2. **Encryption.** A command is built as JSON (`{"n":node,"c":command,"d":data,"t":counter}`), encrypted with AES-128, and hex-encoded.
3. **Transport.** The host sends it over UART to its ESP32. The ESP32 sends it on the bus as a J1939 BAM multi-frame transfer.
4. **Receive.** The receiving ESP32 reassembles the transfer and passes it to its host, which decrypts it and acts on the command.

The host PC does the cryptography because the ESP32 had little free memory with the J1939 stack running.

## Build and run

**Firmware** (ESP-IDF 5.4):

```
cd firmware/j1939-imm
idf.py build flash monitor
```

Set the alert phone number in `firmware/j1939-kle/main/main.cpp` (`DEFAULT_PHONE_NUMBER`) before flashing the KLE node.

**Host** (Python 3, tested on Windows; `msvcrt` is used for keyboard input):

```
pip install -r requirements.txt
cd host/imm
python main.py --identity IMM --port COM3 --mode both
```

MQTT settings come from environment variables: `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`.

**Latency test:**

```
cd host/imm/test_scripts
python complete_latency_test.py --tx-port COM13 --rx-port COM14 --size 10 --messages 50
```

## Results (v1)

End-to-end latency, 50 messages per size, idle bus:

| Data (B) | Bytes on bus | TP.DT packets | Median latency (ms) |
|---------:|-------------:|--------------:|--------------------:|
| 10 | 128 | 19 | 958.7 |
| 50 | 192 | 28 | 1420.4 |
| 150 | 384 | 55 | 2818.8 |
| 200 | 512 | 74 | 3798.7 |

Latency grows by about 50 ms per packet. This matches the 50 ms gap that the BAM transport inserts between packets.
The wire time and the encryption time are both under 1 % of the total.
So the transport layer, not the cryptography or the bus, sets the latency.

## Known limitations and v2 roadmap

A later code review of v1 found the following issues. Each has a planned fix.

| # | Area | Issue in v1 | Fix in v2 |
|---|------|-------------|-----------|
| 1 | Key exchange | Round 2 broadcasts values whose product is the group key, so a passive listener can compute it | Implement the correct Burmester–Desmedt round 2: `X_i = (z_{i+1}/z_{i-1})^{x_i}` |
| 2 | Key exchange | No authentication (open to man-in-the-middle). The prime named `MODP_1024_P` is the 768-bit Oakley Group 1 prime | Authenticated group key exchange (Katz–Yung style, Ed25519 identities) over X25519 or a ≥2048-bit group |
| 3 | Encryption | AES in ECB mode, no integrity check | AES-GCM, or AES-CMAC for authentication only |
| 4 | Freshness | Message counter is tracked but old counters are not rejected (replay) | Reject any counter ≤ last accepted; keep counters across key rotation |
| 5 | J1939 | Any node's TP.CM_BAM sets a local "bus busy" flag, so one forged frame can delay a node's own sends | Remove the flag; CAN arbitration already handles bus access |
| 6 | J1939 | Reassembly buffer size comes from the frame and is not bounded | Cap at 1785 bytes, check packet count, limit open sessions |
| 7 | Host | Keys are printed to the console and stored in clear in SQLite | Remove key prints; keep keys in a protected store |
| 8 | Latency | ~1 s for a 10-byte command, from multi-frame transport and hex/JSON overhead | Authenticate inside a single 8-byte frame (truncated CMAC + counter), SecOC style; move crypto onto the ESP32 |

Items 5 and 6 come from reading the code and are not yet tested on hardware.

**v2 plan:**

1. Build the single-frame authenticated mode (item 8) on the ESP32.
2. Fix the v1 encrypted mode (items 3, 4) so the two modes can be compared fairly.
3. Benchmark both modes: payload size, node count, bus load.
4. Replace the key exchange (items 1, 2).
5. Attack tests: forged frames, replay, man-in-the-middle, forged BAM.

## Safety

Use this only on an isolated bench bus. Never connect it to a real vehicle.
