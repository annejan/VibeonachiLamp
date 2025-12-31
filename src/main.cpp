#include <Arduino.h>
#include <FastLED.h>

#define LED_PIN     6
#define NUM_LEDS    47
#define BRIGHTNESS  255
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB

CRGB leds[NUM_LEDS];

void setup() {
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(BRIGHTNESS);
}

void loop() {
    static uint8_t hue = INT8_MAX;

    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CHSV(hue + i * PI, 255, 255);
    }

    FastLED.show();
    hue--;
    delay(1);
}
