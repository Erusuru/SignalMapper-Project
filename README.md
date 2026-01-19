# 📶 Cellular Signal Mapper & Analysis Suite
### by Ramazan Ertugrul Aydoğan

![Platform](https://img.shields.io/badge/Platform-Android-green)
![Analysis](https://img.shields.io/badge/Analysis-Python-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A comprehensive toolkit for auditing cellular network coverage (4G/LTE/5G), benchmarking hardware performance, and generating high-fidelity signal heatmaps.

This project was originally developed to map the network topology of **Blagoevgrad, Bulgaria**, comparing national carriers (A1, Yettel, Vivacom). However, the **software is universal** and works with any carrier globally.

---

## 📸 Project Visuals

### 📱 Android Application
| Main Interface | Real-time Logging |
|:---:|:---:|
| <img src="app_ui_1.jpeg" width="250" alt="App Status Screen"> | <img src="app_ui_2.jpeg" width="250" alt="Data Collection Screen"> |
| *Status Dashboard* | *Active Data Collection* |

### 🗺️ Coverage Heatmap
<img src="heatmap_preview.png" width="100%" alt="Coverage Heatmap">
*Generated Signal Heatmap (RSRP/SNR) visualized in Kepler.gl*

---

## 🌍 Is this only for Bulgarian Carriers?
**No.**
While the screenshots and sample data show Bulgarian operators (A1, Yettel, Vivacom), the **SignalMapper App** and **Python Analyzers** are carrier-agnostic.
*   **Universal Support:** Works with Turk Telekom, Vodafone, T-Mobile, Verizon, etc.
*   **Dual-SIM Capable:** Logs data from both SIM slots simultaneously.
*   **Roaming Support:** Detects visiting networks (e.g., Turk Telekom roaming in Bulgaria) and handles missing metrics (like null SNR) gracefully.

---

## 📂 Project Structure

### 1. The Android App (`/app`)
A native Kotlin application designed for professional "Drive Testing" without expensive hardware.
*   **Foreground Service:** Uses a persistent notification to prevent Android from killing the app during long trips.
*   **WakeLock:** Keeps the CPU active to log data even when the screen is off (pocket logging).
*   **High-Precision GPS:** Forces the `FusedLocationProvider` into high-accuracy mode (1000ms intervals) to map signal dips to exact street corners.
*   **Telemetry Recorded:** RSRP, SNR/RSRQ, PCI, Network Type.

### 2. The Analysis Suite (`/analysis_scripts`)
Python scripts to turn raw CSV logs into engineering insights.

#### 🧠 `network_analyzer.py` (The Core Engine)
Processes the CSV logs to generate a full network audit.
*   **Stationary Filtering:** Automatically removes data points where the user is sitting still to prevent data skewing.
*   **Spectrum Pollution Detection:** Identifies areas with strong signal (High RSRP) but unusable quality (Low SNR).
*   **Handover Analysis:** Calculates how often the phone switches towers ("Ping-Pong effect").

#### ⚔️ `device_comparison.py` (Hardware Benchmark)
A tool to compare antenna sensitivity between two phones (e.g., **Samsung S25 Ultra vs. Galaxy A52s**). Matches GPS timestamps to calculate average dBm differences.

#### 🗺️ `map_visualizer.py` & `geo_resolver.py`
Tools for resolving Google Maps coordinates and automating high-res heatmap rendering.

---

## 🚀 How to Run

### Part A: The Android App

#### Option 1: Quick Install (No Coding Required)
If you want to use the tool immediately without Android Studio:
1.  Download **[SignalMapper_APK.zip](SignalMapper_APK.zip)** from the file list above.
2.  Extract the ZIP file to get the `.apk`.
3.  Transfer the file to your Android phone.
4.  Tap to install.
    *   *Note: You may need to allow **"Install from Unknown Sources"** in your phone settings since this is a research tool not on the Play Store.*
5.  **Crucial:** On first launch, grant **Location (Always)** and **Phone State** permissions manually if prompted.

#### Option 2: Build from Source (Developers)
1.  Open the root folder in **Android Studio**.
2.  Sync Gradle and run the app on a connected device.

### Part B: The Analysis
1.  Install the required Python libraries:
    ```bash
    pip install pandas numpy matplotlib pytesseract requests playwright
    playwright install
    ```
2.  Place your CSV logs (exported from the app) in the `analysis_scripts` folder.
3.  Run the analyzer:
    ```bash
    python analysis_scripts/network_analyzer.py
    ```

---

## 🔬 Research Findings (Sample)
*Based on 200,000+ data points collected in Blagoevgrad:*
*   **A1 BG:** "Performance King" - Highest peak speeds and aggressive tower switching (60 switches/min).
*   **Yettel:** "Consistency King" - Fewest dead zones and balanced handover logic.
*   **Vivacom:** "Conservative" - Sticky connections; holds onto distant towers too long, causing high spectrum pollution.
*   **Hardware Insight:** The mid-range **Samsung A52s** (plastic back) often outperformed the flagship **S25 Ultra** (metal/glass) in raw signal reception by ~1.2 dBm.

---
*Created for the South-West University "Neofit Rilski" Engineering Department.*
