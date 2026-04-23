#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>

// ======== Wi-Fi & MQTT =========
const char* ssid        = "MyPiHotspot";
const char* password    = "12345678";
const char* mqtt_server = "10.42.0.1";

WiFiClient espClient;
PubSubClient client(espClient);

// ======== MPU6050 =========
Adafruit_MPU6050 mpu1;
Adafruit_MPU6050 mpu2;

bool imu1OK = false;
bool imu2OK = false;

// ======== Calibration Offsets =========
float pitch1_offset = 0, roll1_offset = 0;
float pitch2_offset = 0, roll2_offset = 0;

// ======== Angle Calculation =========
void calculateAngles(float ax, float ay, float az, float &pitch, float &roll) {
  pitch = atan2(ay, sqrt(ax * ax + az * az)) * (180.0 / M_PI);
  roll  = atan2(ax, sqrt(ay * ay + az * az)) * (180.0 / M_PI);
}

// ======== MQTT Reconnect =========
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT... ");
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("connected.");
      client.publish("esp32/status", "ESP32 dual IMU connected.");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 2 seconds...");
      delay(2000);
    }
  }
}

// ======== Safe Read IMU 1 =========
bool readIMU1(float &ax, float &ay, float &az) {
  Wire.beginTransmission(0x68);
  byte error = Wire.endTransmission();
  if (error != 0) {
    Serial.print("[ERROR] IMU 1 (0x68) NACK — error code: ");
    Serial.println(error);
    imu1OK = false;
    return false;
  }
  sensors_event_t a, g, temp;
  mpu1.getEvent(&a, &g, &temp);
  ax = a.acceleration.x;
  ay = a.acceleration.y;
  az = a.acceleration.z;
  imu1OK = true;
  return true;
}

// ======== Safe Read IMU 2 =========
bool readIMU2(float &ax, float &ay, float &az) {
  Wire.beginTransmission(0x69);   // CHANGED: was Wire1
  byte error = Wire.endTransmission();
  if (error != 0) {
    Serial.print("[ERROR] IMU 2 (0x69) NACK — error code: ");
    Serial.println(error);
    imu2OK = false;
    return false;
  }
  sensors_event_t a, g, temp;
  mpu2.getEvent(&a, &g, &temp);
  ax = a.acceleration.x;
  ay = a.acceleration.y;
  az = a.acceleration.z;
  imu2OK = true;
  return true;
}

// ======== Calibration =========
void calibrate() {
  Serial.println("\n--- Calibrating — keep strap in neutral position ---");
  delay(500);

  float ax, ay, az;

  if (readIMU1(ax, ay, az)) {
    calculateAngles(ax, ay, az, pitch1_offset, roll1_offset);
    Serial.print("IMU 1 offset captured — pitch: ");
    Serial.print(pitch1_offset);
    Serial.print("°  roll: ");
    Serial.print(roll1_offset);
    Serial.println("°");
  }

  if (readIMU2(ax, ay, az)) {
    calculateAngles(ax, ay, az, pitch2_offset, roll2_offset);
    Serial.print("IMU 2 offset captured — pitch: ");
    Serial.print(pitch2_offset);
    Serial.print("°  roll: ");
    Serial.print(roll2_offset);
    Serial.println("°");
  }

  Serial.println("--- Calibration complete. Starting readings... ---\n");
}

// ======== Setup =========
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\nStarting ESP32 Dual IMU...");
  Serial.println("IMU 1 → 0x68 | SDA=2, SCL=3");
  Serial.println("IMU 2 → 0x69 | SDA=2, SCL=3");

  IPAddress local_IP(10, 42, 0, 50);
  IPAddress gateway(10, 42, 0, 1);
  IPAddress subnet(255, 255, 255, 0);
  WiFi.config(local_IP, gateway, subnet);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected. IP: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, 1883);
  client.setKeepAlive(60);
  reconnectMQTT();

  // SINGLE I2C BUS
  Wire.begin(2, 3);

  // ---- Init IMU 1 ----
  if (!mpu1.begin(0x68, &Wire)) {
    Serial.println("IMU 1 NOT FOUND!");
    while (1);
  }

  // ---- Init IMU 2 ----
  if (!mpu2.begin(0x69, &Wire)) {   // CHANGED: same bus
    Serial.println("IMU 2 NOT FOUND!");
    while (1);
  }

  Serial.println("Both IMUs ready on single I2C bus.");

  calibrate();
}

// ======== Main Loop =========
void loop() {
  if (!client.connected()) reconnectMQTT();
  client.loop();

  float ax1 = 0, ay1 = 0, az1 = 0;
  float ax2 = 0, ay2 = 0, az2 = 0;
  float pitch1 = 0, roll1 = 0;
  float pitch2 = 0, roll2 = 0;

  Serial.println("--- IMU 1 (0x68) ---");
  if (readIMU1(ax1, ay1, az1)) {
    calculateAngles(ax1, ay1, az1, pitch1, roll1);
    pitch1 -= pitch1_offset;
    roll1  -= roll1_offset;
    Serial.print("  accel_x: "); Serial.print(ax1);
    Serial.print("  accel_y: "); Serial.print(ay1);
    Serial.print("  accel_z: "); Serial.println(az1);
    Serial.print("  pitch:   "); Serial.print(pitch1);
    Serial.print("°  roll: ");   Serial.print(roll1);
    Serial.println("°");
  }

  Serial.println("--- IMU 2 (0x69) ---");
  if (readIMU2(ax2, ay2, az2)) {
    calculateAngles(ax2, ay2, az2, pitch2, roll2);
    pitch2 -= pitch2_offset;
    roll2  -= roll2_offset;
    Serial.print("  accel_x: "); Serial.print(ax2);
    Serial.print("  accel_y: "); Serial.print(ay2);
    Serial.print("  accel_z: "); Serial.println(az2);
    Serial.print("  pitch:   "); Serial.print(pitch2);
    Serial.print("°  roll: ");   Serial.print(roll2);
    Serial.println("°");
  }

  Serial.println("--------------------");

  // ---- Publish ----
  if (imu1OK || imu2OK) {
    char payload[256];
    snprintf(payload, sizeof(payload),
      "{\"imu1\":{\"ok\":%s,\"accel_x\":%.2f,\"accel_y\":%.2f,\"accel_z\":%.2f,\"pitch\":%.2f,\"roll\":%.2f},"
      "\"imu2\":{\"ok\":%s,\"accel_x\":%.2f,\"accel_y\":%.2f,\"accel_z\":%.2f,\"pitch\":%.2f,\"roll\":%.2f}}",
      imu1OK ? "true" : "false", ax1, ay1, az1, pitch1, roll1,
      imu2OK ? "true" : "false", ax2, ay2, az2, pitch2, roll2);

    if (!client.publish("esp32/imu", payload)) {
      Serial.println("Publish failed.");
    }
  } else {
    Serial.println("[WARNING] Both IMUs failed — skipping publish.");
  }

  delay(200);
}