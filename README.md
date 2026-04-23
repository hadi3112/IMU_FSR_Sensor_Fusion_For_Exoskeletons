"""# IMU_FSR_Sensor_Fusion_For_Exoskeletons

##Overview

This project provides a modular pipeline for collecting, processing, and
visualizing data from IMU (Inertial Measurement Units) and FSR (Force
Sensitive Resistor) sensors. It is designed for wearable gait sensing
applications, enabling accurate capture of anatomical movement for
exoskeleton technology development.

The system supports: - Gait analysis of patients - Dataset generation
for machine learning models - LSTM-based classification and sequence
modeling - Real-time sensor fusion for biomechanical insights

---

## 1. Clone Repository

### Windows
```bash
    cd path\to\your\projects
    git clone https://github.com/your-repo.git
    cd IMU_FSR_Sensor_Fusion_For_Exoskeletons

### Linux
```bash
    cd /path/to/your/projects
    git clone https://github.com/your-repo.git
    cd IMU_FSR_Sensor_Fusion_For_Exoskeletons

------------------------------------------------------------------------

## 2. Python Environment Setup

Ensure Python 3.8+ is installed.
```bash
    pip install -r requirements.txt

If requirements.txt is unavailable:
```bash
    pip install paho-mqtt scipy matplotlib numpy

These libraries are used for: - MQTT communication (real-time data
streaming) - Signal processing and dataset handling - Visualization of
sensor data - Numerical computations

------------------------------------------------------------------------

## 3. MQTT Setup (Raspberry Pi Required)

Overview

A Raspberry Pi acts as a local MQTT broker and network controller.

Steps (High-Level)

1.  Create a local network using static IP addressing
2.  Assign static IP to Raspberry Pi
3.  Install and run MQTT broker service
4.  Restrict access to local IP range

TBD

(Add detailed broker setup commands and scripts here)

------------------------------------------------------------------------

## 4. ESP32 Firmware Setup

Navigate to:
```bash
    ESP_codes/

This folder contains template firmware for: - 2 IMUs (mounted on one
leg) - 3 FSR sensors (mounted on foot)

Notes: - Modify sensor configuration based on your setup - Current
implementation supports: - Hip joint angle estimation - Ground reaction
force approximation

Flash using Arduino IDE or ESP-IDF.

------------------------------------------------------------------------

## 5. Running the System

Step 1: Start MQTT Broker (Raspberry Pi)

Step 2: Power ESP32 Devices

Step 3: Run Python UI
```bash
    cd project_root
    python main.py

------------------------------------------------------------------------

## 6. Expected Behavior

-   IMU and FSR data streamed over MQTT
-   Real-time visualization of:
    -   Joint angles
    -   Force signals
    -   Derived temporal features

------------------------------------------------------------------------

## 7. Use Cases

-   Clinical gait analysis and rehabilitation monitoring
-   Dataset creation for machine learning pipelines
-   Training LSTM models for gait phase classification
-   Development and validation of wearable exoskeleton systems

------------------------------------------------------------------------

8. Notes

-   Ensure all devices are on same network
-   Verify MQTT topics are consistent
-   Debug connectivity issues via broker logs
