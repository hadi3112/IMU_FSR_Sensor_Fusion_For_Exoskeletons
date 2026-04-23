#include <WiFi.h>
#include <PubSubClient.h>
#include "esp_system.h"

// ===== WiFi & MQTT =====
const char* ssid = "MyPiHotspot";
const char* password = "12345678";
const char* mqtt_server = "10.42.0.1";

WiFiClient espClient;
PubSubClient client(espClient);

// ===== FSR PINS =====
const int fsrPin1 = 33; //tried 0,1 and 4 but weird behaviour on esp32c2mini, 2 and 3 are the only reliable ADC Pins
const int fsrPin2 = 34;
const int fsrPin3 = 35;

// ===== FILTER =====
#define USE_FILTER 0

float alpha = 0.2;
float filteredValue1 = 0;
float filteredValue2 = 0;
float filteredValue3 = 0;

// ===== MQTT reconnect =====
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting... ");

    String id = "FSRClient-" + String(random(0xffff), HEX);

    if (client.connect(id.c_str())) {
      Serial.println("connected ✔");
      client.publish("esp32/status", "FSR node online");
    } else {
      Serial.print("failed ❌ rc=");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  Serial.println("\nBOOT START");
  Serial.println(ESP.getFreeHeap());

  Serial.print("Reset reason: ");
  Serial.println(esp_reset_reason());

  // ===== WiFi FIRST =====
  Serial.print("[WiFi] Connecting to ");
  Serial.println(ssid);

  IPAddress local_IP(10, 42, 0, 50);     // ESP32 fixed IP
  IPAddress gateway(10, 42, 0, 1);      // Raspberry Pi hotspot + MQTT broker
  IPAddress subnet(255, 255, 255, 0);

  WiFi.config(local_IP, gateway, subnet);
  WiFi.begin(ssid, password);


  while (WiFi.status() != WL_CONNECTED) {
    delay(2000);   // <-- CHANGED (was 500)
    Serial.print(".");
  }

  Serial.println("\n[WiFi] Connected ✔");
  Serial.println(WiFi.localIP());

  // ===== MQTT SECOND =====
  client.setServer(mqtt_server, 1883);

  Serial.println("[MQTT] Connecting...");
  reconnectMQTT();

  // ===== ADC ONLY AFTER NETWORK READY =====
  analogReadResolution(12);

  analogSetPinAttenuation(fsrPin1, ADC_11db);
  analogSetPinAttenuation(fsrPin2, ADC_11db);
  analogSetPinAttenuation(fsrPin3, ADC_11db);

  Serial.println("[ADC] Initialized AFTER WiFi + MQTT ✔");
}

int readFSR(int pin) {
  return analogRead(pin);
}

int processFSR(int raw) {
  return 4095 - raw;
}

void loop() {

  if (!client.connected()) reconnectMQTT();
  client.loop();

  // ===== NOW SAFE ADC SAMPLING =====
  int val1 = processFSR(readFSR(fsrPin1));
  int val2 = processFSR(readFSR(fsrPin2));
  int val3 = processFSR(readFSR(fsrPin3));

  Serial.print("[FSR] 1: "); Serial.print(val1);
  Serial.print(" | 2: "); Serial.print(val2);
  Serial.print(" | 3: "); Serial.println(val3);

  char payload[120];
  snprintf(payload, sizeof(payload),
    "{\"fsr1\":%d,\"fsr2\":%d,\"fsr3\":%d}",
    val1, val2, val3
  );

  Serial.print("[MQTT PAYLOAD] ");
  Serial.println(payload);

  client.publish("esp32/fsr", payload);

  delay(200);
}