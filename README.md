# ⚡ FleetFuel AI - Telematics & Predictive Fuel Intelligence Platform

> **IoT-Based Predictive Fuel Intelligence and Optimization Platform**  
> *A scalable automotive telematics system that senses vehicle behavior, predicts expected fuel consumption, explains inefficiency, estimates fuel waste, and supports operational fleet decisions.*

---

## 📌 1. Project Overview

**FleetFuel AI** bridges the gap between raw vehicle sensor telematics and measurable operational actions. Instead of simply predicting overall fuel usage as a single opaque number, FleetFuel AI closes the loop around four core tenets:

1. **PREDICT**: Calculates a rigorous physical and machine-learning baseline for expected fuel consumption under specific operating conditions.
2. **EXPLAIN**: Provides SHAP-style root-cause attribution breaking down why consumption deviated (e.g., steep road incline, aggressive acceleration, high RPM gear mismatch, tire drag, or prolonged idling).
3. **OPTIMIZE**: Evaluates what-if scenarios (e.g., reducing payload, adjusting cruising speed, optimizing idle times, or adjusting tire pressure).
4. **MEASURE**: Converts physical fuel inefficiency ($L/h$ and excess liters) into business impact (financial cost waste per hour and carbon emission footprint).

---

## 🏗️ 2. End-to-End System Architecture

```text
[ VEHICLE SENSING / REAL-TIME IoT ]
  CAN / OBD-II (ELM327) + Smartphone IMU / Gyroscope (Phyphox) + GPS + Fuel Sensor
                          │
                          ▼
[ EDGE GATEWAY / IoT TELEMETRY ]
  ESP32 / Smartphone Wi-Fi REST API (Normalize, buffer & timestamp tilt angles)
                          │
                          ▼
[ INGESTION & VEHICLE DYNAMICS ENGINE ]
  Python + SAE Automotive Physics Model + SHAP Root-Cause Decomposition
                          │
                          ▼
[ PRESENTATION & CONTROL DASHBOARD ]
  Interactive Streamlit Telematics Simulator (Simultaneous Dynamic Graphs & Sliders)
```

---

## 📱 3. Live IoT Smartphone Integration (Phyphox Sensor Telemetry)

You can turn any smartphone into a real-time **automotive road incline sensor** using **Phyphox** (Physical Phone Experiments):

1. **Install Phyphox:** Download the free **Phyphox** app on Android or iOS.
2. **Same Network:** Connect your laptop and phone to the same Wi-Fi (or mobile hotspot).
3. **Enable Sensor Streaming:**
   - In Phyphox, open **Mechanics** → **Inclination**.
   - Tap the three vertical dots (**⋮**) in the top-right corner.
   - Tap **"Allow remote access"** (shows an IP address, e.g., `http://172.16.87.170:8080`).
4. **Link to Dashboard:**
   - In the sidebar preset dropdown, select **`Live Slope Optimization`**.
   - Paste the phone URL into the **Phone URL** input.
   - **Tilt your phone:** Click **`📲 Poll Phone`** for a single snapshot or check **`🔴 Live Stream`** for continuous real-time updates every second!
   - As you physically tilt your phone like a hill incline, the dashboard recalculates gravity load forces, expected fuel burn, and gives live driving speed advice!

---

## 🎛️ 4. Interactive Sliding Controls (Telemetry Inputs)

The Streamlit dashboard gives operators and engineers real-time sliding options across vehicle telematics categories:

| Control Slider | Range | Units | Technical Significance |
| :--- | :--- | :--- | :--- |
| **🚗 Vehicle Speed** | `0.0 – 140.0` | `km/h` | Determines vehicle velocity, distance rate, and aerodynamic drag force ($F_{aero} \propto v^2$). |
| **⚙️ Engine RPM** | `600 – 5,000` | `RPM` | Determines internal engine friction, BSFC operating band, and transmission gear efficiency. |
| **💨 Acceleration / Braking** | `-4.0 – +4.0` | `m/s²` | Negative represents braking; positive represents inertial demand ($F = m \cdot a$). |
| **📐 Incline Angle (Ascent / Descent)** | `-15.0 – +15.0` | `degrees (°)` | **Ascent (+)** increases gravitational load ($m \cdot g \cdot \sin\theta$). **Descent (-)** enables fuel cut-off. Can be fed live from smartphone gyroscope! |
| **🛢️ Fuel Availability in Tank** | `2.0 – 120.0` | `Liters` | Tracks live tank capacity to calculate real-time driving range and fuel depletion curves. |
| **📦 Cargo Payload** | `0 – 10,000` | `kg` | Directly inflates gross vehicle weight, increasing rolling resistance and uphill gradient forces. |
| **🌡️ Coolant / Engine Temp** | `20 – 115` | `°C` | Cold starts (<80°C) cause cold-engine enrichment penalties; optimal steady state is 85–95°C. |
| **🔘 Tire Pressure** | `20 – 42` | `PSI` | Under-inflation (<32 PSI) increases tire deformation and rolling resistance coefficient ($C_{rr}$). |
| **💵 Fuel Price** | `50.0 – 200.0` | `₹/L` | Translates excess liters burned into operational financial loss per hour (₹/hr). |

---

## 📈 5. Simultaneous Dynamic Visualizations

As you slide any parameter (or tilt your phone), the dashboard computes the physical telemetry equations instantaneously:

### 1. **Operating Curve & Real-Time Telemetry Point (L/h vs Speed)**
- Plots the theoretical **Optimal Expected Baseline** (dashed cyan line) under ideal cruising conditions.
- Plots the **Current Condition Steady-State Curve** (solid indigo line) factoring in current payload weight, road incline angle, and tire pressure across 0–140 km/h.
- Dynamically highlights **Your Current Operating Point** with a glowing diamond marker (emerald green if optimal, amber if moderate, rose red if wasteful).

### 2. **SHAP-Style Root-Cause Inefficiency Decomposition**
Breaks down the exact source of fuel consumption into component contributions:
- **Base Cruise**: Baseline propulsion power.
- **Gradient / Ascent Incline**: Additional fuel burned to overcome gravity uphill.
- **Harsh Acceleration**: Fuel spike caused by inertial surges.
- **Aerodynamic Drag**: High-speed quadratic resistance.
- **High RPM Overhead**: Fuel penalty caused by delayed upshifting.
- **Underinflated Tires**: Mechanical resistance from improper tire pressure.
- **Stationary Idling**: Fuel consumed while stopped.

### 3. **Fuel Depletion & Range Forecast**
- Real-time simulation showing projected fuel level in the tank over trip distance.
- Features a **Critical Reserve Threshold (10 L)** warning horizon.
- Instantly estimates total remaining driving range (km) and operational endurance (hours).

---

## 🚀 6. Quick Scenario Presets

Test pre-configured fleet operational scenarios with a single click from the sidebar dropdown:
- **📱 Live Slope Optimization (IoT)**: Streams live road gradient from your smartphone gyroscope via Phyphox or simulated terrain waves, delivering real-time eco-speed advice.
- **🔋 Maximum Range Extender (Eco-Max)**: 44 km/h, 1300 RPM, 0 kg payload, 120 L fuel, flat road, 36 PSI tires (achieves max theoretical distance of ~1,632 km).
- **🌱 Optimal Highway Cruising (Eco)**: 80 km/h, 1600 RPM, flat ground, 36 PSI tires.
- **⛰️ Steep Mountain Climb (High Load)**: 45 km/h, 2600 RPM, +8.5° ascent, 6,500 kg payload.
- **📉 Downhill Descent (Engine Braking)**: 60 km/h, 1400 RPM, -6.5° descent, zero fuel boost.
- **⚡ Aggressive City Driving**: 55 km/h, 3200 RPM, 2.4 m/s² harsh acceleration, 31 PSI tires.
- **🛑 Stationary Idle (Depot / Loading Bay)**: 0 km/h, 850 RPM, engine on, 1.2 L/h stationary waste.

---

## 💻 7. How to Run Locally

### Prerequisites
- Python 3.9+ installed.

### 1. Install Required Libraries
```bash
pip install -r requirements.txt
```

### 2. Launch the Streamlit App
```bash
streamlit run app.py
```

### 3. View in Browser
Open your browser and navigate to:
```text
http://localhost:8501
```

---

## 📁 8. Project File Structure

```text
FleetFuel-AI/
├── app.py             # Main Streamlit dashboard with structured explanatory comments
├── dashboard.py       # Clean, presentation-ready dashboard version
├── requirements.txt   # Project dependencies (Streamlit, Plotly, NumPy, Pandas, XGBoost, Requests)
├── .gitignore         # Ignores cache and temporary files
└── README.md          # Complete project technical documentation and user guide
```

---

## 🔬 9. Automotive Telematics Physics Model

The fuel rate estimation incorporates standard SAE automotive dynamics:

1. **Total Tractive Force ($F_{tract}$)**:
   $$F_{total} = F_{aero} + F_{roll} + F_{grade} + F_{accel}$$
   - $F_{aero} = \frac{1}{2} \rho C_d A v^2$
   - $F_{roll} = C_{rr}(\text{PSI}) \cdot m \cdot g \cdot \cos(\theta)$
   - $F_{grade} = m \cdot g \cdot \sin(\theta)$
   - $F_{accel} = m \cdot a$

2. **Power Demand**:
   $$P_{\text{demand}} = \frac{F_{total} \cdot v}{1000} \quad (\text{kW})$$

3. **Fuel Consumption Rate**:
   $$\text{Fuel Rate } (L/h) = \text{BSFC} \times P_{\text{demand}} \times \eta_{\text{RPM}} \times \eta_{\text{temp}} + \text{Idle Rate}$$

---

Developed as part of the **FleetFuel AI: IoT-Based Predictive Fuel Intelligence and Optimization Platform** project.
