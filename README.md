# ⚡ FleetFuel AI: IoT Predictive Fuel Telematics & Optimization Platform

> **Physics-Informed Vehicle Telematics, Real-Time Sensor Ingestion, and Inefficiency Attribution**  
> *A full-stack automotive telematics platform that ingests live vehicle and smartphone sensor data, models vehicle dynamics using SAE automotive physics, predicts expected fuel consumption, explains the root causes of fuel waste, and estimates financial loss.*

---

## 📌 1. Project Overview & Problem Statement

### The Problem
Commercial fleets and heavy transport vehicles lose thousands of liters of fuel every month. Traditional fleet management systems only track GPS dots on a map, leaving fleet managers unable to answer critical questions:
* *Why is Truck A consuming 40% more fuel than Truck B on the same delivery route?*
* *Is excess fuel consumption caused by a steep mountain climb, aggressive acceleration, underinflated tires, or prolonged idling?*

### The Solution: FleetFuel AI
**FleetFuel AI** bridges the gap between raw vehicle sensors and actionable fleet intelligence. Operating on four core pillars:

1. **SENSE**: Ingests live telemetry from smartphones (gyroscopes/accelerometers), IoT devices (ESP32/OBD-II), or simulated trucks via **MQTT (TCP & WebSockets)** and **REST APIs**.
2. **PREDICT**: Computes expected fuel consumption using rigorous **SAE automotive physics equations** (aerodynamic drag, rolling friction, gravitational gradient, and inertial acceleration).
3. **EXPLAIN**: Performs **SHAP-style root-cause decomposition** to pinpoint exactly which factors (hill ascent, harsh acceleration, aerodynamic drag, high RPM, or flat tires) caused the fuel spike.
4. **OPTIMIZE & MEASURE**: Translates wasted liters into real-time financial impact (₹/hour) and provides dynamic driving recommendations (e.g., target cruising speeds, gear-shift advice).

---

## 🏗️ 2. System Architecture

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                        SENSING / TELEMETRY LAYER                      │
 └────────────────────────────────────────────────────────────────────────┘
        │                                              │
  [ Smartphone Gyroscope ]                       [ Standalone CLI ]
  (Browser Motion / Phyphox)                   (simulate_iot_truck.py)
        │                                              │
        │ HTML5 Orientation                            │ Raw Telematics
        │ (WebSocket Port 8884)                        │ (TCP Port 1883)
        ▼                                              ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                    PUBLIC CLOUD MQTT BROKER                           │
 │                     (broker.hivemq.com)                               │
 │                  Topic: fleetfuel/telematics                          │
 └────────────────────────────────────────────────────────────────────────┘
                                │
                                │ Subscribe & Receive
                                ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │              PROCESSING & VEHICLE DYNAMICS ENGINE                      │
 │    • SAE Classical Physics Model (Force -> Power -> Fuel Rate)         │
 │    • Persistent Singleton Telemetry Store (@st.cache_resource)         │
 │    • SHAP-Style Inefficiency Factor Decomposition                      │
 └────────────────────────────────────────────────────────────────────────┘
                                │
                                │ Real-Time Rendering
                                ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                   PRESENTATION & DASHBOARD LAYER                       │
 │    • Streamlit Web UI (KPI Cards, Sliders, Scenario Presets)          │
 │    • Plotly Dynamic Visualizations (Operating Curves & Depletion)      │
 │    • Accessible on Localhost, Cloudflare Tunnel, or Streamlit Cloud    │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 3. Automotive Physics Engine Explained

The vehicle model in [`calculate_fuel_telematics()`](file:///c:/Users/gy897/OneDrive/Desktop/New%20folder/app.py) calculates fuel consumption using classical mechanics in 5 simple steps:

### Step 1: Unit Conversion
Vehicle speed is measured in $km/h$, but physics formulas require meters per second ($m/s$):
$$\text{Velocity } (v) = \frac{\text{Speed (km/h)}}{3.6}$$
$$\text{Total Mass } (m) = 4,800\text{ kg (Base Truck)} + \text{Cargo Payload (kg)}$$

### Step 2: The 4 Resistive Forces (in Newtons)
When a vehicle drives, the powertrain must overcome four physical forces:

| Force | Formula | Meaning in Plain English |
| :--- | :--- | :--- |
| **1. Aerodynamic Drag ($F_{\text{aero}}$)** | $\frac{1}{2} \rho C_d A v^2$ | Wind resistance pushing against the front of the truck. Increases quadratically with speed ($v^2$). |
| **2. Rolling Resistance ($F_{\text{roll}}$)** | $C_{rr} \cdot m \cdot g \cdot \cos(\theta)$ | Friction between tires and the asphalt. Under-inflated tires (<35 PSI) deform more and increase drag. |
| **3. Gravitational Gradient ($F_{\text{grade}}$)** | $m \cdot g \cdot \sin(\theta)$ | **Ascent (+):** Gravity pulls the truck backward down the hill (wastes fuel).<br>**Descent (-):** Gravity pushes the truck forward (saves fuel). |
| **4. Inertial Acceleration ($F_{\text{accel}}$)** | $m \cdot a$ | Newton's 2nd Law ($F = ma$). Surging forward demands heavy engine torque. Braking ($a \le 0$) consumes no extra fuel. |

$$\text{Total Tractive Force } (F_{\text{total}}) = F_{\text{aero}} + F_{\text{roll}} + F_{\text{grade}} + F_{\text{accel}}$$

### Step 3: Mechanical Power Demand
$$\text{Power Demand } (P) = \frac{F_{\text{total}} \cdot v}{1000} \quad (\text{in Kilowatts, kW})$$

### Step 4: Engine Efficiency & Thermal Penalties
* **Cold Engine Penalty:** Coolant temperature below 85°C burns extra fuel to warm up the engine block.
* **High RPM Penalty:** Operating above 1,800 RPM in the wrong transmission gear causes excessive internal frictional drag.
* **Idling Fuel Rate:** A stationary diesel truck burns $\sim 1.2\text{ L/h}$ at 800 RPM.

### Step 5: Actual vs. Expected Baseline Fuel Consumption
$$\text{Actual Fuel Rate } (L/h) = (\text{Idle Auxiliary}) + (P_{\text{demand}} \times \text{BSFC} \times \eta_{\text{cold}} \times \eta_{\text{RPM}})$$
* **BSFC ($0.265$):** Brake Specific Fuel Consumption constant converting mechanical power ($kW$) to diesel fuel volume ($L/h$).
* **Expected Baseline:** What the truck *would* burn under ideal eco-driving conditions (0° incline, proper 35 PSI tires, steady cruising speed).

---

## 📱 4. Live Smartphone Sensor Telemetry (Two Modes)

FleetFuel AI allows any smartphone to act as an automotive tilt sensor:

### Mode A: Cloud MQTT Broker (Recommended for Cloud Deployments)
* **How it works:** Open the dashboard link on your phone. In the sidebar, select **Live Slope Optimization** $\rightarrow$ **Cloud MQTT Broker**.
* **Browser Motion Transmitter:** Tap **"Enable This Phone's Sensor"**. The browser reads your phone's gyroscope (`DeviceOrientationEvent`) and broadcasts live pitch angles over WebSockets (`wss://broker.hivemq.com:8884/mqtt`).
* **Why it works anywhere:** Works across 4G/5G and home Wi-Fi because it uses the public MQTT broker.

### Mode B: Local Wi-Fi (Phyphox app, Localhost Only)
* **How it works:** Uses the free **Phyphox** physics app on the same local Wi-Fi router.
* **Why it only works on Localhost:** Your phone has a private IP address (e.g., `172.16.87.170`). A cloud server located in a remote data center cannot route to a private home/campus LAN (RFC 1918). Therefore, use Mode A when viewing deployed links.

---

## 🎛️ 5. Interactive Sliding Controls (Telemetry Inputs)

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

## 📊 6. Simultaneous Dynamic Visualizations

As you slide any parameter (or tilt your phone), the dashboard computes the physical telemetry equations instantaneously:

### 1. **Operating Curve & Real-Time Operating Point (L/h vs Speed)**
- Plots the theoretical **Optimal Expected Baseline** (dashed cyan line) under ideal cruising conditions.
- Plots the **Current Condition Steady-State Curve** (solid indigo line) factoring in current payload weight, road incline angle, and tire pressure across 0–140 km/h.
- Dynamically highlights **Your Current Operating Point** with a glowing diamond marker:
  - 🟢 **Emerald Green:** Fuel rate within ±10% of optimal target.
  - 🟡 **Amber Yellow:** Fuel rate moderately elevated (10% to 35% above target).
  - 🔴 **Rose Red:** Severe fuel penalty (>35% above target).

### 2. **SHAP-Style Root-Cause Inefficiency Breakdown**
Horizontal waterfall-style breakdown attributing excess fuel consumption to specific mechanical sources:
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

## 🚀 7. Quick Scenario Presets

Test pre-configured fleet operational scenarios with a single click from the sidebar dropdown:
- **📱 Live Slope Optimization (IoT)**: Streams live road gradient from your smartphone gyroscope via MQTT or Phyphox, delivering real-time eco-speed advice.
- **🔋 Maximum Range Extender (Eco-Max)**: 44 km/h, 1300 RPM, 0 kg payload, 120 L fuel, flat road, 36 PSI tires (achieves max theoretical distance of ~1,632 km).
- **🌱 Optimal Highway Cruising (Eco)**: 80 km/h, 1600 RPM, flat ground, 36 PSI tires.
- **⛰️ Steep Mountain Climb (High Load)**: 45 km/h, 2600 RPM, +8.5° ascent, 6,500 kg payload.
- **📉 Downhill Descent (Engine Braking)**: 60 km/h, 1400 RPM, -6.5° descent, zero fuel boost.
- **⚡ Aggressive City Driving**: 55 km/h, 3200 RPM, 2.4 m/s² harsh acceleration, 31 PSI tires.
- **🛑 Stationary Idle (Depot / Loading Bay)**: 0 km/h, 850 RPM, engine on, 1.2 L/h stationary waste.

---

## 💻 8. How to Run Locally

### Prerequisites
* Python 3.9+ installed.

### 1. Clone the Repository
```bash
git clone https://github.com/asphixyy/FleetFuel-Optimizer.git
cd FleetFuel-Optimizer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Dashboard
```bash
streamlit run app.py
```
Open your browser and navigate to **`http://localhost:8501`**.

---

## 🌐 9. Public Deployment Options

### Option 1: Streamlit Community Cloud (Permanent Cloud Link)
1. Fork or push this repository to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and select `app.py`.
3. Your app is live at a permanent public URL (e.g., `https://fleetfuel-optimizer-xxxx.streamlit.app`).

### Option 2: Cloudflare Tunnel (Proxying from Localhost)
To share your local machine without setting up port forwarding:
```powershell
.\cloudflared.exe tunnel --url http://127.0.0.1:8501
```
Cloudflare will provide a temporary `trycloudflare.com` URL that tunnels directly to your laptop.

---

## 📁 10. Repository File Structure

```text
FleetFuel-Optimizer/
│
├── app.py                # Main Streamlit application with UI, physics model, and MQTT ingestion
├── dashboard.py          # Alternative clean presentation version
├── simulate_iot_truck.py # Standalone CLI Python script simulating live truck telemetry via MQTT
├── requirements.txt      # Required Python packages (streamlit, plotly, paho-mqtt, etc.)
├── cloudflared.exe       # Cloudflare Tunnel binary for local proxying
└── README.md             # Complete technical documentation and user guide
```

---

## 🎓 11. Beginner's Viva / Interview Cheatsheet

### Q1: What is the primary objective of FleetFuel AI?
> **Answer:** FleetFuel AI is an automotive telematics platform that predicts expected vehicle fuel consumption using physics models, detects inefficiencies (such as steep slopes, aggressive acceleration, or high RPM), and attributes fuel waste to specific root causes with financial cost impact.

### Q2: Why combine physics modeling with machine learning?
> **Answer:** Pure machine learning models require massive datasets and can make unrealistic predictions when exposed to unseen operating conditions. Physics equations (SAE tractive forces) provide an explainable, reliable baseline, while ML accounts for complex driver behavior and real-world variance.

### Q3: How does road incline affect fuel consumption?
> **Answer:** When climbing an incline angle $\theta$, gravity pulls the vehicle backward with a force $F_g = m \cdot g \cdot \sin(\theta)$. For a heavy 7,000 kg truck on a 10° slope, this adds over 11,000 Newtons of resistive force, requiring massive extra engine power and increasing fuel consumption by 300% to 500%. On downhills ($\theta < 0$), gravity assists propulsion, allowing the vehicle to coast with zero throttle.

### Q4: Why did local Wi-Fi work on localhost but fail on cloud deployments?
> **Answer:** Local Wi-Fi relies on private IP addresses (e.g., `172.16.87.170` defined under RFC 1918) that are only reachable within the same home/campus router. A cloud data center server runs on the public internet and cannot route into a private home network. We resolved this by integrating a cloud MQTT broker (`broker.hivemq.com`), allowing the phone and server to exchange data over public WebSockets.

### Q5: What does `@st.cache_resource` do in Streamlit?
> **Answer:** Streamlit reruns the entire Python script from top to bottom on every user interaction. `@st.cache_resource` tells Streamlit to create the MQTT background network connection only once and keep it alive in memory across all reruns, preventing repeated client reconnections and data loss.

### Q6: What is BSFC (Brake Specific Fuel Consumption)?
> **Answer:** BSFC measures the fuel efficiency of an internal combustion engine that burns fuel and produces rotational shaft power. In our model, $0.265$ converts mechanical Kilowatts ($kW$) of power demand into diesel liters consumed per hour ($L/h$).

---

## 👥 Contributors & Acknowledgments
* **Author:** Shivam Yadav ([@asphixyy](https://github.com/asphixyy))
* Built with **Python**, **Streamlit**, **Plotly**, and **Paho-MQTT**.
