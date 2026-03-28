#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>

// ─── Pins (adjust to your wiring) ────────────────────────────────────────────
#define RST_PIN  21
#define SS_PIN   5

MFRC522          mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key rfidKey;

// ─── Helpers ──────────────────────────────────────────────────────────────────
uint8_t xorChecksum(const uint8_t* data, size_t len) {
    uint8_t c = 0;
    for (size_t i = 0; i < len; i++) c ^= data[i];
    return c;
}

// Returns true if block number is a sector trailer (every 4th: 3,7,11,15,...)
bool isSectorTrailer(uint8_t block) {
    return ((block + 1) % 4 == 0);
}

// Authenticate and write one 16-byte block
bool writeBlock(uint8_t blockNum, uint8_t* data16) {
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A,
        blockNum, &rfidKey, &mfrc522.uid
    );
    if (status != MFRC522::STATUS_OK) {
        Serial.printf("[WRITE] Auth failed block %d: %s\n",
                      blockNum, mfrc522.GetStatusCodeName(status));
        return false;
    }
    status = mfrc522.MIFARE_Write(blockNum, data16, 16);
    if (status != MFRC522::STATUS_OK) {
        Serial.printf("[WRITE] Write failed block %d: %s\n",
                      blockNum, mfrc522.GetStatusCodeName(status));
        return false;
    }
    return true;
}

// ─── Core write function ──────────────────────────────────────────────────────
// Expects buf = full binary packet (642 bytes), prefixed with 4-byte length
bool writePacketToTag(const uint8_t* buf, uint32_t dataLen) {

    // Validate magic
    if (buf[0] != 0xA5 || buf[1] != 0x5A) {
        Serial.println("[WRITE] Bad magic bytes");
        return false;
    }

    // Validate checksum
    uint8_t expected = xorChecksum(buf, dataLen - 1);
    if (expected != buf[dataLen - 1]) {
        Serial.printf("[WRITE] Checksum mismatch: got 0x%02X, expected 0x%02X\n",
                      buf[dataLen - 1], expected);
        return false;
    }

    Serial.println("[WRITE] Packet valid — place tag on reader...");

    // Wait for tag
    uint32_t deadline = millis() + 15000;
    while (millis() < deadline) {
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial())
            break;
        delay(100);
    }
    if (!mfrc522.uid.size) {
        Serial.println("[WRITE] No tag detected — timeout");
        return false;
    }

    // Print UID
    Serial.print("[WRITE] Tag UID: ");
    for (byte i = 0; i < mfrc522.uid.size; i++)
        Serial.printf("%02X ", mfrc522.uid.uidByte[i]);
    Serial.println();

    // Build write buffer: 4-byte length header + packet
    uint8_t  lenHeader[4] = {
        (uint8_t)(dataLen >> 24), (uint8_t)(dataLen >> 16),
        (uint8_t)(dataLen >>  8), (uint8_t)(dataLen)
    };

    uint32_t totalBytes = 4 + dataLen;
    uint32_t offset     = 0;
    uint8_t  blockNum   = 4;        // start after reserved blocks 0-3
    uint8_t  block[16];

    while (offset < totalBytes) {
        if (isSectorTrailer(blockNum)) { blockNum++; continue; }

        memset(block, 0, 16);
        for (uint8_t i = 0; i < 16 && offset < totalBytes; i++, offset++) {
            block[i] = (offset < 4) ? lenHeader[offset] : buf[offset - 4];
        }

        if (!writeBlock(blockNum, block)) {
            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
            return false;
        }
        Serial.printf("[WRITE] Block %d OK\n", blockNum);
        blockNum++;
    }

    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    Serial.printf("[WRITE] Done — wrote %d bytes across %d blocks\n",
                  totalBytes, blockNum - 4);
    return true;
}

// ─── Receive .bin file over Serial then write to tag ─────────────────────────
#define MAX_PACKET 700
uint8_t  rxBuf[MAX_PACKET];
uint32_t rxLen = 0;

void receiveAndWrite() {
    Serial.println("[SERIAL] Waiting for .bin file (4-byte length + data)...");

    // Read 4-byte length
    uint32_t deadline = millis() + 30000;
    while (Serial.available() < 4 && millis() < deadline) delay(10);
    if (Serial.available() < 4) { Serial.println("[SERIAL] Timeout"); return; }

    uint8_t lb[4];
    Serial.readBytes(lb, 4);
    rxLen = ((uint32_t)lb[0] << 24) | ((uint32_t)lb[1] << 16)
          | ((uint32_t)lb[2] <<  8) |  (uint32_t)lb[3];

    if (rxLen == 0 || rxLen > MAX_PACKET) {
        Serial.printf("[SERIAL] Invalid length: %d\n", rxLen);
        return;
    }

    // Read packet bytes
    uint32_t received = 0;
    deadline = millis() + 10000;
    while (received < rxLen && millis() < deadline) {
        if (Serial.available())
            rxBuf[received++] = Serial.read();
    }

    if (received < rxLen) {
        Serial.printf("[SERIAL] Only got %d of %d bytes\n", received, rxLen);
        return;
    }

    Serial.printf("[SERIAL] Received %d bytes OK\n", rxLen);

    if (writePacketToTag(rxBuf, rxLen))
        Serial.println("ACK: write successful");
    else
        Serial.println("ERR: write failed");
}

// ─── Setup / Loop ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    SPI.begin();
    mfrc522.PCD_Init();
    for (byte i = 0; i < 6; i++) rfidKey.keyByte[i] = 0xFF;
    Serial.println("=== RFID Writer Ready ===");
    Serial.println("Send .bin file over Serial to write to tag");
}

void loop() {
    if (Serial.available() >= 4)
        receiveAndWrite();
}