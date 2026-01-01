#include <Adafruit_BNO055.h>
#include <Arduino.h>
#include <FastLED.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <Wire.h>
#include <time.h>
#include <utility/imumaths.h>

extern "C" {
void led_render_quat(float qw, float qx, float qy, float qz, float sun_lon,
                     float sun_lat, uint8_t *out_rgb);
}
#define tex_day day_tex
#define tex_night night_tex

// ================= CONFIG =================
#define NUM_LEDS 300
#define LED_PIN 5
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define BRIGHTNESS 255

#define I2C_SDA 21
#define I2C_SCL 22

#define AXIAL_TILT (23.44f * PI / 180.0f)

#define SETUP_BUTTON_PIN 0     // BOOT knop op veel ESP32's
#define WIFI_TIMEOUT_MS 300000 // 5 minuten
// ==========================================

struct Config {
  float brightness;
  float time_scale;

  bool has_utc;
  time_t utc_epoch;

  char wifi_ssid[32];
  char wifi_pass[64];
};

Config cfg;
Preferences prefs;

CRGB leds[NUM_LEDS];
uint8_t led_buffer[NUM_LEDS * 3];

Adafruit_BNO055 bno(55, 0x28);

imu::Quaternion q_zero(1, 0, 0, 0);

// ---------- quaternion helpers ----------
imu::Quaternion quatInverse(const imu::Quaternion &q) {
  return imu::Quaternion(q.w(), -q.x(), -q.y(), -q.z());
}

imu::Quaternion quatMul(const imu::Quaternion &a, const imu::Quaternion &b) {
  return imu::Quaternion(
      a.w() * b.w() - a.x() * b.x() - a.y() * b.y() - a.z() * b.z(),
      a.w() * b.x() + a.x() * b.w() + a.y() * b.z() - a.z() * b.y(),
      a.w() * b.y() - a.x() * b.z() + a.y() * b.w() + a.z() * b.x(),
      a.w() * b.z() + a.x() * b.y() - a.y() * b.x() + a.z() * b.w());
}

void loadConfig() {
  prefs.begin("globe", true);
  cfg.brightness = prefs.getFloat("brightness", 0.5f);
  cfg.time_scale = prefs.getFloat("time_scale", 240.0f);
  cfg.has_utc = prefs.getBool("has_utc", false);
  cfg.utc_epoch = prefs.getULong64("utc", 0);

  prefs.getString("ssid", cfg.wifi_ssid, sizeof(cfg.wifi_ssid));
  prefs.getString("pass", cfg.wifi_pass, sizeof(cfg.wifi_pass));
  prefs.end();
}

void saveConfig() {
  prefs.begin("globe", false);
  prefs.putFloat("brightness", cfg.brightness);
  prefs.putFloat("time_scale", cfg.time_scale);
  prefs.putBool("has_utc", cfg.has_utc);
  prefs.putULong64("utc", cfg.utc_epoch);
  prefs.putString("ssid", cfg.wifi_ssid);
  prefs.putString("pass", cfg.wifi_pass);
  prefs.end();
}

WebServer server(80);
bool setupMode = false;
unsigned long setupStartTime = 0;

const char PAGE_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body>
<h2>Earth Globe Setup</h2>

<form action="/save" method="POST">
Brightness:<br>
<input type="range" min="0" max="1" step="0.01" name="brightness" value="%BRIGHT%"><br><br>

Time scale:<br>
<input type="number" name="time" value="%TIME%"><br><br>

<button type="submit">Save & Reboot</button>
</form>

<br>
<form action="/recenter" method="POST">
<button type="submit">Recenter IMU</button>
</form>

<hr>
<h3>WiFi / Time</h3>

<form action="/wifi" method="POST">
SSID:<br>
<input name="ssid"><br>
Password:<br>
<input name="pass" type="password"><br><br>
<button type="submit">Save WiFi</button>
</form>

<br>
<form action="/ntp" method="POST">
<button type="submit">Sync NTP Now</button>
</form>

</body>
</html>
)rawliteral";

String page() {
  String p = PAGE_HTML;
  p.replace("%BRIGHT%", String(cfg.brightness));
  p.replace("%TIME%", String(cfg.time_scale));
  return p;
}

bool connectWiFiClient() {
  if (strlen(cfg.wifi_ssid) == 0)
    return false;

  WiFi.mode(WIFI_STA);
  WiFi.begin(cfg.wifi_ssid, cfg.wifi_pass);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    if (millis() - start > 15000)
      return false;
  }
  return true;
}

void startSetupWiFi() {
  setupMode = true;
  setupStartTime = millis();

  WiFi.mode(WIFI_AP);
  WiFi.softAP("EarthGlobe-Setup");

  server.on("/", []() { server.send(200, "text/html", page()); });

  server.on("/save", HTTP_POST, []() {
    cfg.brightness = server.arg("brightness").toFloat();
    cfg.time_scale = server.arg("time").toFloat();
    saveConfig();
    server.send(200, "text/plain", "Saved. Rebooting...");
    delay(500);
    ESP.restart();
  });

  server.on("/recenter", HTTP_POST, []() {
    q_zero = bno.getQuat();
    server.send(200, "text/plain", "IMU recentered");
  });

  server.on("/ntp", HTTP_POST, []() {
    if (!connectWiFiClient()) {
      server.send(500, "text/plain", "WiFi connect failed");
      return;
    }

    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

    time_t now;
    int retries = 20;
    while (retries-- && time(&now) < 100000) {
      delay(500);
    }

    if (now < 100000) {
      server.send(500, "text/plain", "NTP failed");
      WiFi.disconnect(true);
      return;
    }

    cfg.utc_epoch = now;
    cfg.has_utc = true;
    saveConfig();

    WiFi.disconnect(true);

    server.send(200, "text/plain", "NTP synced & saved");
  });

  server.on("/wifi", HTTP_POST, []() {
    strlcpy(cfg.wifi_ssid, server.arg("ssid").c_str(), sizeof(cfg.wifi_ssid));
    strlcpy(cfg.wifi_pass, server.arg("pass").c_str(), sizeof(cfg.wifi_pass));
    saveConfig();
    server.send(200, "text/plain", "WiFi saved");
  });

  server.begin();
  Serial.println("🌐 Setup WiFi active @ 192.168.4.1");
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(I2C_SDA, I2C_SCL);

  if (!bno.begin()) {
    Serial.println("❌ BNO055 not detected");
    while (1)
      ;
  }
  bno.setExtCrystalUse(true);

  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  FastLED.clear();

  // initial orientation = reference
  q_zero = bno.getQuat();

  loadConfig();

  if (cfg.has_utc) {
    struct timeval tv;
    tv.tv_sec = cfg.utc_epoch;
    tv.tv_usec = 0;
    settimeofday(&tv, nullptr);
    Serial.println("⏱ RTC set from stored UTC");
  }

  FastLED.setBrightness(cfg.brightness * 255);
  pinMode(SETUP_BUTTON_PIN, INPUT_PULLUP);
  if (digitalRead(SETUP_BUTTON_PIN) == LOW) {
    startSetupWiFi();
  }

  Serial.println("✅ Earth Globe started");
}

// ================= LOOP =================
void loop() {
  // ---------- timing ----------
  static uint32_t last_ms = millis();
  uint32_t now_ms = millis();
  float dt = (now_ms - last_ms) * 0.001f;
  last_ms = now_ms;

  // ---------- SETUP MODE (WiFi config) ----------
  if (setupMode) {
    server.handleClient();

    if (millis() - setupStartTime > WIFI_TIMEOUT_MS) {
      Serial.println("⏱ Setup timeout, rebooting");
      ESP.restart();
    }
    return; // do NOT render while configuring
  }

  // ---------- TIME (RTC / stored UTC) ----------
  time_t now;
  time(&now); // works with or without WiFi
  struct tm *utc = gmtime(&now);

  // seconds since midnight
  float seconds_today =
      utc->tm_hour * 3600.0f + utc->tm_min * 60.0f + utc->tm_sec;

  // ---------- SUN POSITION ----------
  // longitude: time of day
  float sun_lon = 2.0f * PI * (seconds_today / 86400.0f);

  // latitude: seasons
  float year_phase = 2.0f * PI * (utc->tm_yday / 365.2422f);

  float sun_lat = sinf(year_phase) * AXIAL_TILT;

  // ---------- IMU ----------
  imu::Quaternion q_imu = bno.getQuat();

  // relative orientation to startup reference
  imu::Quaternion q_rel = quatMul(q_imu, quatInverse(q_zero));

  // camera quaternion = inverse
  imu::Quaternion q_view = quatInverse(q_rel);

  // ---------- RENDER ----------
  led_render_quat(q_view.w(), q_view.x(), q_view.y(), q_view.z(), sun_lon,
                  sun_lat, led_buffer);

  // ---------- COPY TO LEDS ----------
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i].r = led_buffer[i * 3 + 0];
    leds[i].g = led_buffer[i * 3 + 1];
    leds[i].b = led_buffer[i * 3 + 2];
  }

  FastLED.show();
}
