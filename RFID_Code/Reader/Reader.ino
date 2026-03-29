/**
 * Reader.ino
 *
 * - Press 'r' in Serial Monitor to read an RFID patient card
 * - Hold the button (GPIO 33) to signal the laptop to record and ask a question
 *
 * Wiring:
 *   MFRC522  RST → GPIO 21   SS → GPIO 5    SPI defaults (18/19/23)
 *   Buzzer → GPIO 15
 *   Button → GPIO 33 (other leg to GND)
 */

#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <driver/i2s.h>

// ─── Pins ─────────────────────────────────────────────────────────────────────
#define RST_PIN     21
#define SS_PIN       5
#define BUZZER_PIN  15
#define BUTTON_PIN  33   // INPUT_PULLUP, active LOW
#define LAUNCH_PIN  32   // INPUT_PULLUP, active LOW → launches processvoice

// ─── Patient structs ──────────────────────────────────────────────────────────
struct Allergy {
    char    name[17];
    uint8_t severity;
    uint8_t symptomCount;
    char    symptoms[5][17];
};

struct Patient {
    uint16_t patientId;
    uint32_t dateOfBirth;
    uint32_t dateOfVisit;
    char     gender;
    float    height;
    float    weight;
    float    bmi;
    float    bloodPressure;
    uint8_t  severityOfVisit;
    char     name[33];
    char     conditions[33];
    char     medications[33];
    char     familyHistory[33];
    uint8_t  allergyCount;
    Allergy  allergies[5];
};

// ─── I2S (MAX98357A) ──────────────────────────────────────────────────────────
#define I2S_BCLK    26
#define I2S_LRC     25
#define I2S_DOUT    22
#define AUDIO_SAMPLE_RATE 16000

MFRC522          mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key rfidKey;

// ─── I2S init ─────────────────────────────────────────────────────────────────
void initI2S() {
    i2s_config_t cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate          = AUDIO_SAMPLE_RATE,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = 8,
        .dma_buf_len          = 512,
        .use_apll             = false,
        .tx_desc_auto_clear   = true,
    };
    i2s_pin_config_t pins = {
        .bck_io_num   = I2S_BCLK,
        .ws_io_num    = I2S_LRC,
        .data_out_num = I2S_DOUT,
        .data_in_num  = I2S_PIN_NO_CHANGE,
    };
    i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pins);
}

// ─── Audio receive & play ─────────────────────────────────────────────────────
void playAudioFromSerial(uint32_t numBytes) {
    Serial.printf("[AUDIO] Playing %u bytes\n", numBytes);
    uint8_t buf[512];
    uint32_t received = 0;

    while (received < numBytes) {
        uint32_t toRead = min((uint32_t)sizeof(buf), numBytes - received);
        uint32_t got = 0;
        uint32_t deadline = millis() + 3000;

        while (got < toRead && millis() < deadline) {
            int avail = Serial.available();
            if (avail > 0) {
                int r = Serial.readBytes(buf + got, min((int)(toRead - got), avail));
                got += r;
            }
        }
        if (got == 0) break;  // timeout

        size_t written;
        i2s_write(I2S_NUM_0, buf, got, &written, portMAX_DELAY);
        received += got;
    }

    // Flush I2S with silence so last samples play out
    uint8_t silence[512] = {};
    size_t written;
    i2s_write(I2S_NUM_0, silence, sizeof(silence), &written, portMAX_DELAY);

    Serial.println("AUDIO_DONE");
}

// ─── Incoming serial command handler ─────────────────────────────────────────
void checkSerialCommands() {
    if (!Serial.available()) return;

    char cmdBuf[96];
    int len = Serial.readBytesUntil('\n', cmdBuf, sizeof(cmdBuf) - 1);
    if (len > 0 && cmdBuf[len - 1] == '\r') len--;
    cmdBuf[len] = '\0';

    if (strcmp(cmdBuf, "AUDIO_START") == 0) {
        uint8_t lenBytes[4];
        Serial.readBytes(lenBytes, 4);
        uint32_t numBytes = ((uint32_t)lenBytes[0] << 24) | ((uint32_t)lenBytes[1] << 16)
                          | ((uint32_t)lenBytes[2] <<  8) |  (uint32_t)lenBytes[3];
        playAudioFromSerial(numBytes);
    }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
uint8_t xorChecksum(const uint8_t* data, size_t len) {
    uint8_t c = 0;
    for (size_t i = 0; i < len; i++) c ^= data[i];
    return c;
}

bool isSectorTrailer(uint8_t block) {
    return ((block + 1) % 4 == 0);
}

bool readBlock(uint8_t blockNum, uint8_t* out16) {
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A,
        blockNum, &rfidKey, &mfrc522.uid
    );
    if (status != MFRC522::STATUS_OK) {
        Serial.printf("[READ] Auth failed block %d: %s\n",
                      blockNum, mfrc522.GetStatusCodeName(status));
        return false;
    }
    byte    bufSize = 18;
    uint8_t tmp[18];
    status = mfrc522.MIFARE_Read(blockNum, tmp, &bufSize);
    if (status != MFRC522::STATUS_OK) {
        Serial.printf("[READ] Read failed block %d: %s\n",
                      blockNum, mfrc522.GetStatusCodeName(status));
        return false;
    }
    memcpy(out16, tmp, 16);
    return true;
}

// ─── Decode ───────────────────────────────────────────────────────────────────
bool decodePacket(const uint8_t* buf, uint32_t len, Patient& p) {
    if (buf[0] != 0xA5 || buf[1] != 0x5A) {
        Serial.println("[DECODE] Bad magic bytes");
        return false;
    }

    uint8_t expected = xorChecksum(buf, len - 1);
    if (expected != buf[len - 1]) {
        Serial.printf("[DECODE] Checksum fail — got 0x%02X expected 0x%02X\n",
                      buf[len - 1], expected);
        return false;
    }

    uint32_t o = 2;
    p.patientId       = ((uint16_t)buf[o] << 8) | buf[o+1];             o += 2;
    p.dateOfBirth     = ((uint32_t)buf[o]<<24)|((uint32_t)buf[o+1]<<16)
                      |((uint32_t)buf[o+2]<<8)|(uint32_t)buf[o+3];     o += 4;
    p.dateOfVisit     = ((uint32_t)buf[o]<<24)|((uint32_t)buf[o+1]<<16)
                      |((uint32_t)buf[o+2]<<8)|(uint32_t)buf[o+3];     o += 4;
    p.gender          = (char)buf[o++];
    p.height          = ((buf[o] << 8) | buf[o+1]) / 10.0f;             o += 2;
    p.weight          = ((buf[o] << 8) | buf[o+1]) / 10.0f;             o += 2;
    p.bmi             = ((buf[o] << 8) | buf[o+1]) / 100.0f;            o += 2;
    p.bloodPressure   = ((buf[o] << 8) | buf[o+1]) / 10.0f;             o += 2;
    p.severityOfVisit = buf[o++];

    memcpy(p.name,          buf + o, 32); p.name[32]          = '\0'; o += 32;
    memcpy(p.conditions,    buf + o, 32); p.conditions[32]    = '\0'; o += 32;
    memcpy(p.medications,   buf + o, 32); p.medications[32]   = '\0'; o += 32;
    memcpy(p.familyHistory, buf + o, 32); p.familyHistory[32] = '\0'; o += 32;

    p.allergyCount = buf[o++];
    for (uint8_t i = 0; i < 5; i++) {
        memcpy(p.allergies[i].name, buf + o, 16);
        p.allergies[i].name[16] = '\0';                                  o += 16;
        p.allergies[i].severity     = buf[o++];
        p.allergies[i].symptomCount = buf[o++];
        for (uint8_t j = 0; j < 5; j++) {
            memcpy(p.allergies[i].symptoms[j], buf + o, 16);
            p.allergies[i].symptoms[j][16] = '\0';                       o += 16;
        }
    }
    return true;
}

// ─── Pretty print ─────────────────────────────────────────────────────────────
void printPatient(const Patient& p) {
    Serial.println("\n╔══════════════════════════════════╗");
    Serial.println(  "║         PATIENT RECORD           ║");
    Serial.println(  "╚══════════════════════════════════╝");
    Serial.printf("  ID          : %d\n",       p.patientId);
    Serial.printf("  Name        : %s\n",       p.name);
    Serial.printf("  DOB         : %08lu\n",    (unsigned long)p.dateOfBirth);
    Serial.printf("  Visit Date  : %08lu\n",    (unsigned long)p.dateOfVisit);
    Serial.printf("  Severity    : %d / 5\n",   p.severityOfVisit);
    Serial.printf("  Gender      : %c\n",       p.gender);
    Serial.printf("  Height      : %.1f cm\n",  p.height);
    Serial.printf("  Weight      : %.1f kg\n",  p.weight);
    Serial.printf("  BMI         : %.2f\n",     p.bmi);
    Serial.printf("  Blood Pres. : %.1f mmHg\n",p.bloodPressure);
    Serial.printf("  Conditions  : %s\n",       p.conditions);
    Serial.printf("  Medications : %s\n",       p.medications);
    Serial.printf("  Family Hx   : %s\n",       p.familyHistory);

    Serial.println("  ── Allergies ──────────────────────");
    if (p.allergyCount == 0) {
        Serial.println("  None on record");
    } else {
        for (uint8_t i = 0; i < p.allergyCount; i++) {
            Serial.printf("  [%d] %-16s  severity: %d\n",
                          i + 1,
                          p.allergies[i].name,
                          p.allergies[i].severity);
            for (uint8_t j = 0; j < p.allergies[i].symptomCount; j++)
                Serial.printf("      • %s\n", p.allergies[i].symptoms[j]);
        }
    }
    Serial.println("════════════════════════════════════\n");
    tone(BUZZER_PIN, 1000, 150);
}

// ─── RFID read ────────────────────────────────────────────────────────────────
#define MAX_PACKET 700
uint8_t rawBuf[MAX_PACKET];

void readTagAndDecode() {
    Serial.print("[READ] Tag UID: ");
    for (byte i = 0; i < mfrc522.uid.size; i++)
        Serial.printf("%02X ", mfrc522.uid.uidByte[i]);
    Serial.println();

    uint8_t block4[16];
    if (!readBlock(4, block4)) {
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    uint32_t dataLen = ((uint32_t)block4[0] << 24) | ((uint32_t)block4[1] << 16)
                     | ((uint32_t)block4[2] <<  8) |  (uint32_t)block4[3];

    if (dataLen == 0 || dataLen > MAX_PACKET) {
        Serial.printf("[READ] Invalid length: %d\n", dataLen);
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    Serial.printf("[READ] Packet length: %d bytes\n", dataLen);

    uint32_t firstChunk = min((uint32_t)12, dataLen);
    memcpy(rawBuf, block4 + 4, firstChunk);
    uint32_t collected = firstChunk;
    uint8_t  blockNum  = 5;

    while (collected < dataLen) {
        if (isSectorTrailer(blockNum)) { blockNum++; continue; }

        uint8_t tmp[16];
        if (!readBlock(blockNum, tmp)) {
            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
            return;
        }
        uint32_t chunk = min((uint32_t)16, dataLen - collected);
        memcpy(rawBuf + collected, tmp, chunk);
        collected += chunk;
        blockNum++;
    }

    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    Serial.printf("[READ] Read complete — %d bytes\n", collected);

    Patient p;
    if (decodePacket(rawBuf, dataLen, p)) {
        printPatient(p);
        Serial.printf("PATIENT_ID:%d\n", p.patientId);
    } else {
        Serial.println("[READ] Decode failed");
    }

    // Reset the reader so it can detect the next card cleanly
    mfrc522.PCD_Init();
}

// ─── Setup / Loop ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(460800);
    SPI.begin();
    mfrc522.PCD_Init();
    for (byte i = 0; i < 6; i++) rfidKey.keyByte[i] = 0xFF;
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(LAUNCH_PIN, INPUT_PULLUP);
    initI2S();

    Serial.println("=== RFID Patient Reader ===");
    Serial.println("Scanning for cards continuously | Hold button to ask a question");
}

void loop() {
    checkSerialCommands();

    // Continuously scan for RFID cards
    if (mfrc522.PICC_IsNewCardPresent()) {
        if (mfrc522.PICC_ReadCardSerial()) {
            readTagAndDecode();
            delay(2000);  // prevent double-reads from the same card
        }
    } else {
        delay(50);  // short pause between polls to keep the antenna stable
    }

    // Button held → tell Python to start recording from laptop mic
    if (digitalRead(BUTTON_PIN) == LOW) {
        delay(20);  // debounce
        if (digitalRead(BUTTON_PIN) != LOW) return;

        Serial.println("RECORD_START");
        while (digitalRead(BUTTON_PIN) == LOW) delay(10);
        Serial.println("RECORD_STOP");
    }

    // Launch button → tell PC to start processvoice.py
    if (digitalRead(LAUNCH_PIN) == LOW) {
        delay(20);  // debounce
        if (digitalRead(LAUNCH_PIN) != LOW) return;

        Serial.println("LAUNCH_APP");
        while (digitalRead(LAUNCH_PIN) == LOW) delay(10);  // wait for release
    }
}
