# Cellular Signal Mapper & Analysis Suite
# Ramazan Ertugrul Aydogan
![Platform](https://img.shields.io/badge/Platform-Android-green)
![Analysis](https://img.shields.io/badge/Analysis-Python-blue)

This project consists of two parts: a native **Android Application** to log cellular telemetry (RSRP, SNR, PCI) and a **Python Analysis Suite** to process that data into engineering reports and coverage heatmaps.

## 📱 1. Android Application
Located in the root directory.
*   **Language:** Kotlin
*   **Key Features:**
    *   Dual-SIM support (SubscriptionManager API).
    *   Foreground Service with `WakeLock` for continuous 1Hz logging.
    *   High-Accuracy GPS (FusedLocationProvider).

## 📊 2. Analysis Scripts
Located in `/analysis_scripts`.
*   **network_analyzer.py:** Generates engineering reports (Signal quality, Pollution analysis, Handover logic).
*   **device_comparison.py:** Compares hardware sensitivity between two devices (e.g., S25 Ultra vs A52s).
*   **ocr_processor.py:** Extracts signal data from screenshots (if manual logging is required).

## 🚀 How to Run
1.  **Android:** Open the root folder in Android Studio and build the APK.
2.  **Python:** Install dependencies:
    ```bash
    pip install pandas numpy matplotlib pytesseract requests
    ```

---
*Developed for Cellular Network Auditing Research.*
