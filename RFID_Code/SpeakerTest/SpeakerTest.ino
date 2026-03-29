/**
 * SpeakerTest.ino
 *
 * Plays a 440 Hz sine wave tone through the MAX98357A I2S amp.
 * If you hear a tone, the wiring and amp are working.
 *
 * Wiring:
 *   MAX98357A BCLK → GPIO 26
 *   MAX98357A LRC  → GPIO 25
 *   MAX98357A DIN  → GPIO 22
 *   MAX98357A SD   → 3.3V
 *   MAX98357A VIN  → 3.3V
 */

#include <Arduino.h>
#include <driver/i2s.h>

#define I2S_BCLK  26
#define I2S_LRC   25
#define I2S_DOUT  22

#define SAMPLE_RATE 16000
#define TONE_HZ     440
#define AMPLITUDE   10000   // lower = quieter, max 32767

void setup() {
    Serial.begin(115200);

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

    i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pins);

    Serial.println("Playing 440 Hz tone — you should hear a beep.");
}

void loop() {
    // Generate one cycle of samples and stream continuously
    const int SAMPLES = 256;
    int16_t buf[SAMPLES];

    for (int i = 0; i < SAMPLES; i++) {
        float t = (float)i / SAMPLE_RATE;
        buf[i] = (int16_t)(AMPLITUDE * sin(2.0f * PI * TONE_HZ * t));
    }

    size_t written;
    i2s_write(I2S_NUM_0, buf, sizeof(buf), &written, portMAX_DELAY);
}
