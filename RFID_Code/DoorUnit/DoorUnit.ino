/**
 * DoorUnit.ino
 *
 * Self-contained ESP32 door reader — no laptop or Raspberry Pi needed.
 *
 * Flow:
 *   1. Boot → connect to WiFi
 *   2. Wait for RFID card (auto-detects, no prompt needed)
 *   3. Decode patient data from card
 *   4. Call Gemini API for a spoken briefing (text)
 *   5. Call Google TTS API to synthesize the text to audio
 *   6. Play audio through MAX98357A I2S amp → speaker
 *   7. Loop back to step 2
 *
 * Wiring:
 *   MFRC522  SDA  → GPIO 5     (SPI CS)
 *   MFRC522  SCK  → GPIO 18    (SPI CLK)
 *   MFRC522  MOSI → GPIO 23    (SPI MOSI)
 *   MFRC522  MISO → GPIO 19    (SPI MISO)
 *   MFRC522  RST  → GPIO 21
 *   MFRC522  VCC  → 3.3V       ⚠️ NOT 5V
 *   MAX98357A BCLK → GPIO 26
 *   MAX98357A LRC  → GPIO 25
 *   MAX98357A DIN  → GPIO 22
 *   MAX98357A SD   → 3.3V      (always on)
 *   MAX98357A VIN  → 3.3V
 *   Buzzer    +    → GPIO 15
 *
 * Libraries required (install via Arduino Library Manager):
 *   - MFRC522 by GithubCommunity
 *   - ArduinoJson by Benoit Blanchon (v6.x)
 *   - ESP32 Arduino core (includes WiFi, HTTPClient, I2S driver)
 */

#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>
#include "mbedtls/base64.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "secrets.h"   // Copy secrets.h.example → secrets.h and fill in your credentials

// ─── Pins ─────────────────────────────────────────────────────────────────────
#define RST_PIN    21
#define SS_PIN      5
#define BUZZER_PIN 15
#define I2S_BCLK   26
#define I2S_LRC    25
#define I2S_DOUT   22

#define SAMPLE_RATE  8000
#define I2S_PORT     I2S_NUM_0
#define WAV_HEADER   44

// ─── RFID ─────────────────────────────────────────────────────────────────────
MFRC522            mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key rfidKey;

// ─── Patient structs (mirrors RFID.py binary encoding) ───────────────────────
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

// ─── Helpers ──────────────────────────────────────────────────────────────────
uint8_t xorChecksum(const uint8_t* data, size_t len) {
    uint8_t c = 0;
    for (size_t i = 0; i < len; i++) c ^= data[i];
    return c;
}

bool isSectorTrailer(uint8_t block) {
    return ((block + 1) % 4 == 0);
}

void beep(int freq, int ms) {
    tone(BUZZER_PIN, freq, ms);
    delay(ms + 50);
}

// ─── I2S ──────────────────────────────────────────────────────────────────────
void i2s_init() {
    i2s_config_t cfg = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate          = SAMPLE_RATE,
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
    i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
    i2s_set_pin(I2S_PORT, &pins);
}

void play_pcm(const uint8_t* data, size_t len) {
    const size_t CHUNK = 512;
    size_t written;
    for (size_t offset = 0; offset < len; offset += CHUNK) {
        size_t chunk = min(CHUNK, len - offset);
        i2s_write(I2S_PORT, data + offset, chunk, &written, portMAX_DELAY);
    }
    delay(200);
}

// ─── RFID — copied directly from Reader.ino ───────────────────────────────────
bool readBlock(uint8_t blockNum, uint8_t* out16) {
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockNum, &rfidKey, &mfrc522.uid);
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

#define MAX_PACKET 700
uint8_t rawBuf[MAX_PACKET];

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
    p.patientId       = ((uint16_t)buf[o] << 8) | buf[o+1]; o += 2;
    p.dateOfBirth     = ((uint32_t)buf[o]<<24)|((uint32_t)buf[o+1]<<16)
                      |((uint32_t)buf[o+2]<<8)|(uint32_t)buf[o+3]; o += 4;
    p.dateOfVisit     = ((uint32_t)buf[o]<<24)|((uint32_t)buf[o+1]<<16)
                      |((uint32_t)buf[o+2]<<8)|(uint32_t)buf[o+3]; o += 4;
    p.gender          = (char)buf[o++];
    p.height          = ((buf[o] << 8) | buf[o+1]) / 10.0f; o += 2;
    p.weight          = ((buf[o] << 8) | buf[o+1]) / 10.0f; o += 2;
    p.bmi             = ((buf[o] << 8) | buf[o+1]) / 100.0f; o += 2;
    p.bloodPressure   = ((buf[o] << 8) | buf[o+1]) / 10.0f; o += 2;
    p.severityOfVisit = buf[o++];

    memcpy(p.name,          buf+o, 32); p.name[32]          = '\0'; o += 32;
    memcpy(p.conditions,    buf+o, 32); p.conditions[32]    = '\0'; o += 32;
    memcpy(p.medications,   buf+o, 32); p.medications[32]   = '\0'; o += 32;
    memcpy(p.familyHistory, buf+o, 32); p.familyHistory[32] = '\0'; o += 32;

    p.allergyCount = buf[o++];
    for (uint8_t i = 0; i < 5; i++) {
        memcpy(p.allergies[i].name, buf+o, 16);
        p.allergies[i].name[16] = '\0'; o += 16;
        p.allergies[i].severity     = buf[o++];
        p.allergies[i].symptomCount = buf[o++];
        for (uint8_t j = 0; j < 5; j++) {
            memcpy(p.allergies[i].symptoms[j], buf+o, 16);
            p.allergies[i].symptoms[j][16] = '\0'; o += 16;
        }
    }
    return true;
}

// Identical to Reader.ino's readTagAndDecode — waits for card, reads all blocks
bool readTagAndDecode(Patient& p) {
    Serial.println("[READ] Place tag on reader...");

    uint32_t deadline = millis() + 15000;
    while (millis() < deadline) {
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial())
            break;
        delay(100);
    }
    if (!mfrc522.uid.size) {
        Serial.println("[READ] No tag detected");
        return false;
    }

    Serial.print("[READ] Tag UID: ");
    for (byte i = 0; i < mfrc522.uid.size; i++)
        Serial.printf("%02X ", mfrc522.uid.uidByte[i]);
    Serial.println();

    uint8_t block4[16];
    if (!readBlock(4, block4)) {
        mfrc522.PICC_HaltA(); mfrc522.PCD_StopCrypto1();
        return false;
    }

    uint32_t dataLen = ((uint32_t)block4[0] << 24) | ((uint32_t)block4[1] << 16)
                     | ((uint32_t)block4[2] <<  8) |  (uint32_t)block4[3];

    if (dataLen == 0 || dataLen > MAX_PACKET) {
        Serial.printf("[READ] Invalid length: %d\n", dataLen);
        mfrc522.PICC_HaltA(); mfrc522.PCD_StopCrypto1();
        return false;
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
            mfrc522.PICC_HaltA(); mfrc522.PCD_StopCrypto1();
            return false;
        }
        uint32_t chunk = min((uint32_t)16, dataLen - collected);
        memcpy(rawBuf + collected, tmp, chunk);
        collected += chunk;
        blockNum++;
    }

    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    Serial.printf("[READ] Read complete — %d bytes\n", collected);

    return decodePacket(rawBuf, dataLen, p);
}

// ─── Build patient summary for Gemini ────────────────────────────────────────
String buildPatientSummary(const Patient& p) {
    String s;
    s.reserve(512);
    s += "Patient ID: ";     s += p.patientId;       s += "\n";
    s += "Name: ";           s += p.name;             s += "\n";
    s += "DOB: ";            s += p.dateOfBirth;      s += "\n";
    s += "Gender: ";         s += p.gender;           s += "\n";
    s += "Height: ";         s += p.height;           s += " cm\n";
    s += "Weight: ";         s += p.weight;           s += " kg\n";
    s += "BMI: ";            s += p.bmi;              s += "\n";
    s += "Blood Pressure: "; s += p.bloodPressure;    s += " mmHg\n";
    s += "Severity: ";       s += p.severityOfVisit;  s += "/5\n";
    s += "Conditions: ";     s += p.conditions;       s += "\n";
    s += "Medications: ";    s += p.medications;      s += "\n";
    s += "Family History: "; s += p.familyHistory;    s += "\n";

    if (p.allergyCount > 0) {
        s += "Allergies:\n";
        for (uint8_t i = 0; i < p.allergyCount; i++) {
            s += "  - ";
            s += p.allergies[i].name;
            s += " (severity ";
            s += p.allergies[i].severity;
            s += ")";
            for (uint8_t j = 0; j < p.allergies[i].symptomCount; j++) {
                s += (j == 0) ? ": " : ", ";
                s += p.allergies[i].symptoms[j];
            }
            s += "\n";
        }
    } else {
        s += "Allergies: None\n";
    }
    return s;
}

// ─── Gemini API ───────────────────────────────────────────────────────────────
const char* GEMINI_SYSTEM =
    "You are a clinical briefing assistant. A doctor is about to enter a patient's room. "
    "Give a quick spoken briefing covering the most important things first. "
    "Rules: talk like a human, keep it under 15 seconds of speaking, lead with severity and "
    "allergies, no bullet points or markdown, speak naturally, start with the patient name.";

String callGemini(const String& summary) {
    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;
    http.setTimeout(15000);

    String url = "https://generativelanguage.googleapis.com/v1beta/models/"
                 "gemini-2.0-flash:generateContent?key=";
    url += GEMINI_KEY;

    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<3072> req;
    req["system_instruction"]["parts"][0]["text"] = GEMINI_SYSTEM;
    req["contents"][0]["parts"][0]["text"] =
        "Patient data:\n\n" + summary + "\n\nGive me a spoken clinical briefing.";
    req["generationConfig"]["maxOutputTokens"] = 120;

    String body;
    serializeJson(req, body);

    int code = http.POST(body);
    if (code != 200) {
        Serial.printf("[GEMINI] HTTP %d\n", code);
        Serial.println(http.getString());
        http.end();
        return "";
    }

    String response = http.getString();
    http.end();

    StaticJsonDocument<4096> resp;
    if (deserializeJson(resp, response)) return "";
    return resp["candidates"][0]["content"]["parts"][0]["text"].as<String>();
}

// ─── Google TTS API ───────────────────────────────────────────────────────────
uint8_t* callTTS(const String& text, size_t& outLen) {
    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;
    http.setTimeout(20000);

    String url = "https://texttospeech.googleapis.com/v1/text:synthesize?key=";
    url += TTS_KEY;

    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<512> req;
    req["input"]["text"]                  = text;
    req["voice"]["languageCode"]          = "en-US";
    req["voice"]["name"]                  = "en-US-Standard-D";
    req["audioConfig"]["audioEncoding"]   = "LINEAR16";
    req["audioConfig"]["sampleRateHertz"] = SAMPLE_RATE;

    String body;
    serializeJson(req, body);

    int code = http.POST(body);
    if (code != 200) {
        Serial.printf("[TTS] HTTP %d\n", code);
        Serial.println(http.getString());
        http.end();
        return nullptr;
    }

    String response = http.getString();
    http.end();

    // Extract base64 audioContent manually to avoid a second large allocation
    int keyPos = response.indexOf("\"audioContent\"");
    if (keyPos == -1) { Serial.println("[TTS] audioContent not found"); return nullptr; }
    int start = response.indexOf('"', keyPos + 14) + 1;
    int end   = response.indexOf('"', start);
    if (start <= 0 || end <= start) { Serial.println("[TTS] Parse failed"); return nullptr; }

    size_t  b64Len    = end - start;
    size_t  decodedMax = (b64Len * 3) / 4 + 4;
    uint8_t* pcm = (uint8_t*)malloc(decodedMax);
    if (!pcm) { Serial.println("[TTS] malloc failed"); return nullptr; }

    size_t actualLen = 0;
    int ret = mbedtls_base64_decode(pcm, decodedMax, &actualLen,
                                    (const uint8_t*)(response.c_str() + start), b64Len);
    response = "";  // free immediately after decode

    if (ret != 0) { Serial.printf("[TTS] base64 error: %d\n", ret); free(pcm); return nullptr; }

    // Strip 44-byte WAV header Google TTS prepends
    if (actualLen > WAV_HEADER) {
        memmove(pcm, pcm + WAV_HEADER, actualLen - WAV_HEADER);
        outLen = actualLen - WAV_HEADER;
    } else {
        outLen = actualLen;
    }
    return pcm;
}

// ─── Setup ────────────────────────────────────────────────────────────────────
void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    Serial.begin(115200);
    pinMode(BUZZER_PIN, OUTPUT);

    SPI.begin();
    mfrc522.PCD_Init();
    for (byte i = 0; i < 6; i++) rfidKey.keyByte[i] = 0xFF;

    i2s_init();

    Serial.printf("Connecting to %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nConnected — IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());

    beep(1000, 200);
    Serial.println("=== Door Unit Ready ===");
}

// ─── Main loop ────────────────────────────────────────────────────────────────
void loop() {
    // Wait for card — same as Reader.ino, just runs automatically
    Patient patient;
    if (!readTagAndDecode(patient)) {
        delay(500);
        return;
    }

    beep(1000, 150);
    Serial.printf("[READ] Patient: %s (ID %d)\n", patient.name, patient.patientId);
    Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());

    // Call Gemini
    String summary  = buildPatientSummary(patient);
    String briefing = callGemini(summary);
    if (briefing.isEmpty()) {
        Serial.println("[GEMINI] Empty response");
        beep(400, 400);
        return;
    }
    Serial.printf("[GEMINI] %s\n", briefing.c_str());

    // Call TTS and play
    size_t   pcmLen = 0;
    uint8_t* pcm    = callTTS(briefing, pcmLen);
    if (!pcm) {
        Serial.println("[TTS] Failed");
        beep(400, 400);
        return;
    }
    Serial.printf("[TTS] Playing %d bytes\n", pcmLen);
    play_pcm(pcm, pcmLen);
    free(pcm);

    Serial.println("--- Ready for next patient ---\n");
    delay(2000);
}
