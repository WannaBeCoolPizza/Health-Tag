/**
 * mic_sender.ino
 * 
 * Records audio from INMP441 mic over I2S while button is held,
 * then streams raw 16-bit PCM over Serial to PC.
 * 
 * Wiring (INMP441):
 *   VDD  → 3.3V
 *   GND  → GND
 *   SCK  → GPIO 14
 *   WS   → GPIO 15
 *   SD   → GPIO 32
 *   L/R  → GND  (selects left channel)
 * 
 * Button:
 *   One side → GPIO 0
 *   Other    → GND
 */

#include <driver/i2s.h>

// ─── Pin Definitions ──────────────────────────────────────────────────────────
#define BUTTON_PIN   0
#define I2S_SCK      14
#define I2S_WS       15
#define I2S_SD       32

// ─── Audio Settings ───────────────────────────────────────────────────────────
#define SAMPLE_RATE     16000
#define BITS_PER_SAMPLE 16
#define CHANNELS        1
#define DMA_BUF_COUNT   8
#define DMA_BUF_LEN     256

// ─── Transfer markers ─────────────────────────────────────────────────────────
// PC looks for these to know when audio starts and ends
const uint8_t START_MARKER[] = {0xAA, 0xBB, 0xCC, 0xDD};
const uint8_t END_MARKER[]   = {0xDD, 0xCC, 0xBB, 0xAA};

void setup() {
    Serial.begin(921600);   // high baud for audio throughput
    pinMode(BUTTON_PIN, INPUT_PULLUP);

    // Configure I2S
    i2s_config_t i2s_config = {
        .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate          = SAMPLE_RATE,
        .bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT,  // INMP441 outputs 32-bit frames
        .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count        = DMA_BUF_COUNT,
        .dma_buf_len          = DMA_BUF_LEN,
        .use_apll             = false,
        .tx_desc_auto_clear   = false,
        .fixed_mclk           = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num   = I2S_SCK,
        .ws_io_num    = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = I2S_SD
    };

    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
    i2s_zero_dma_buffer(I2S_NUM_0);

    Serial.println("MIC READY — hold button to record");
}

void loop() {
    // Wait for button press (active LOW)
    if (digitalRead(BUTTON_PIN) == LOW) {
        delay(20);  // debounce
        if (digitalRead(BUTTON_PIN) != LOW) return;

        Serial.println("RECORDING...");

        // Send start marker so PC knows audio is coming
        Serial.write(START_MARKER, sizeof(START_MARKER));

        // Buffer for 32-bit I2S samples
        const int BUF_SAMPLES = 256;
        int32_t   i2s_buf[BUF_SAMPLES];
        int16_t   pcm_buf[BUF_SAMPLES];
        size_t    bytes_read;

        // Stream audio while button is held
        while (digitalRead(BUTTON_PIN) == LOW) {
            i2s_read(I2S_NUM_0, i2s_buf, sizeof(i2s_buf), &bytes_read, portMAX_DELAY);

            int samples = bytes_read / 4;
            for (int i = 0; i < samples; i++) {
                // INMP441 data is in the top 24 bits of the 32-bit frame
                // Shift down to 16-bit PCM
                pcm_buf[i] = (int16_t)(i2s_buf[i] >> 11);
            }

            Serial.write((uint8_t*)pcm_buf, samples * 2);
        }

        // Send end marker
        Serial.write(END_MARKER, sizeof(END_MARKER));
        Serial.println("\nDONE");
    }
}
