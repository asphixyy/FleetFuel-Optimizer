import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import json
import time
import paho.mqtt.client as mqtt
import streamlit.components.v1 as components

# ==============================================================================
# MQTT CLOUD TELEMATICS SUBSCRIBER (broker.hivemq.com)
# ==============================================================================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "fleetfuel/telematics"

# Thread-safe global store for background MQTT packets
class MQTTTelemetryStore:
    def __init__(self):
        self.incline = 0.0
        self.speed = None
        self.rpm = None
        self.last_time = None
        self.packet_count = 0
        self.status = "Connecting..."
        self.client = None

@st.cache_resource
def get_mqtt_telemetry_store():
    store = MQTTTelemetryStore()

    def _on_mqtt_connect(client, userdata, flags, rc, properties=None):
        store.status = "Connected"
        client.subscribe(MQTT_TOPIC)
        client.subscribe("fleetfuel/+/telematics")

    def _on_mqtt_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if "incline" in payload:
                store.incline = round(float(payload["incline"]), 1)
            if "speed" in payload:
                store.speed = round(float(payload["speed"]), 1)
            if "rpm" in payload:
                store.rpm = int(payload["rpm"])
            store.last_time = time.strftime("%H:%M:%S")
            store.packet_count += 1
        except Exception:
            pass

    # Try TCP 1883 first, fallback to WSS 8884 if port 1883 is blocked by cloud firewall
    connected = False
    try:
        api_ver = mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None
        mq_client = mqtt.Client(api_ver, client_id=f"fleetfuel_tcp_{int(time.time()*1000)%100000}")
        mq_client.on_connect = _on_mqtt_connect
        mq_client.on_message = _on_mqtt_message
        mq_client.connect(MQTT_BROKER, 1883, 30)
        mq_client.loop_start()
        store.client = mq_client
        store.status = "Connected (TCP 1883)"
        connected = True
    except Exception:
        pass

    if not connected:
        try:
            api_ver = mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None
            mq_client = mqtt.Client(api_ver, client_id=f"fleetfuel_ws_{int(time.time()*1000)%100000}", transport="websockets")
            mq_client.ws_set_options(path="/mqtt")
            mq_client.tls_set()
            mq_client.on_connect = _on_mqtt_connect
            mq_client.on_message = _on_mqtt_message
            mq_client.connect(MQTT_BROKER, 8884, 30)
            mq_client.loop_start()
            store.client = mq_client
            store.status = "Connected (WSS 8884)"
        except Exception as e:
            store.status = f"Offline ({e})"

    return store

global_telemetry_store = get_mqtt_telemetry_store()

# ==============================================================================
# 1. PAGE SETUP
# ==============================================================================
st.set_page_config(
    page_title="FleetFuel AI - Telematics Dashboard",
    page_icon="⚡",
    layout="wide"
)

# Styling: Elegant darker yellowish/amber tone for Telematics sidebar
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e190b 0%, #161208 100%) !important;
        border-right: 1px solid rgba(234, 179, 8, 0.25) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #facc15 !important;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #fef08a !important;
    }
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div[role="slider"] {
        background-color: #eab308 !important;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("⚡ FLEETFUEL AI: Predictive Fuel Telematics Platform")
st.caption("Real-Time Vehicle Dynamics, ML Inefficiency Detection & Operational Intelligence")

# ==============================================================================
# 2. VEHICLE DYNAMICS & FUEL PREDICTION FUNCTION
# ==============================================================================
def calculate_fuel_telematics(speed, rpm, accel, incline, payload, fuel_avail, temp, psi, fuel_price=95.0):
    """
    Computes vehicle forces, power demand, and expected vs actual fuel consumption.
    Simple to explain to judges:
    Total Force = Aero Drag + Rolling Resistance + Hill Gradient + Acceleration Force
    """
    v_ms = speed / 3.6                          # Convert km/h to m/s
    total_mass = 4800.0 + payload               # 4800 kg base vehicle weight + cargo (kg)
    theta = np.radians(incline)                 # Incline angle in radians

    # 1. Aerodynamic drag force: F = 0.5 * rho * Cd * A * v^2
    f_aero = 0.5 * 1.225 * 0.55 * 4.2 * (v_ms ** 2)

    # 2. Rolling resistance: affected by under-inflated tire pressure
    crr = 0.012 + (max(0.0, (35.0 - psi) * 0.0004) if psi < 35.0 else 0.0)
    f_roll = crr * total_mass * 9.81 * np.cos(theta)

    # 3. Hill Incline force: positive = uphill (ascent), negative = downhill (descent)
    f_grade = total_mass * 9.81 * np.sin(theta)

    # 4. Acceleration force: F = m * a (only when accelerating forward)
    f_accel = total_mass * accel if accel > 0 else 0.0

    # Total tractive force and power demand (kW)
    total_force = f_aero + f_roll + f_grade + f_accel
    power_kw = max(0.0, (total_force * v_ms) / 1000.0)

    # Thermal & RPM efficiency penalties
    cold_penalty = 1.0 + max(0.0, (85.0 - temp) * 0.003)      # Cold engine consumes more
    rpm_penalty = 1.0 + (0.15 * ((rpm / 1600.0) - 1.0) ** 2 if rpm > 1800 else 0.0)

    # Idle fuel rate (L/h)
    idle_lh = 1.2 * (rpm / 800.0)

    # Actual fuel rate (L/h) vs Ideal expected baseline (L/h)
    if speed < 1.0:
        actual_lh = idle_lh * cold_penalty
        expected_lh = idle_lh
    else:
        actual_lh = (idle_lh * 0.4) + (power_kw * 0.265 * cold_penalty * rpm_penalty)
        # Expected baseline assumes optimal driving (0 incline, 0 accel, optimal rpm)
        opt_power = ((0.012 * total_mass * 9.81 + f_aero) * v_ms) / 1000.0
        expected_lh = (idle_lh * 0.35) + (opt_power * 0.25)

    actual_lh = max(0.6, actual_lh)
    expected_lh = max(0.5, expected_lh)

    # Derived fuel metrics
    excess_fuel_lh = actual_lh - expected_lh
    dev_pct = (excess_fuel_lh / expected_lh) * 100.0
    km_per_l = (speed / actual_lh) if speed > 1.0 else 0.0
    l_per_100km = (actual_lh / speed * 100.0) if speed > 1.0 else 99.9
    waste_cost_per_hr = max(0.0, excess_fuel_lh) * fuel_price

    # Range and endurance
    remaining_hours = fuel_avail / actual_lh
    remaining_range_km = remaining_hours * speed

    # SHAP-Style factor breakdown (L/h)
    factors = {
        "Base Cruising": round(max(0.2, expected_lh * 0.6), 2),
        "Hill Gradient (Ascent)": round(max(0.0, (f_grade * v_ms / 1000.0) * 0.26), 2) if incline > 0 else 0.0,
        "Harsh Acceleration": round(max(0.0, (f_accel * v_ms / 1000.0) * 0.26), 2) if accel > 0 else 0.0,
        "Aero Drag (High Speed)": round(max(0.0, (f_aero * v_ms / 1000.0) * 0.25), 2),
        "High RPM Inefficiency": round(max(0.0, actual_lh * (rpm_penalty - 1.0)), 2),
        "Underinflated Tires": round(max(0.0, 0.4 if psi < 32 else 0.0), 2)
    }

    return {
        "actual_lh": round(actual_lh, 2),
        "expected_lh": round(expected_lh, 2),
        "dev_pct": round(dev_pct, 1),
        "excess_fuel_lh": round(excess_fuel_lh, 2),
        "km_per_l": round(km_per_l, 2),
        "l_per_100km": round(l_per_100km, 2),
        "waste_cost_per_hr": round(waste_cost_per_hr, 2),
        "remaining_range_km": round(remaining_range_km, 1),
        "remaining_hours": round(remaining_hours, 1),
        "power_kw": round(power_kw, 1),
        "factors": factors
    }

# ==============================================================================
# 3. SIDEBAR CONTROLS & SLIDERS
# ==============================================================================
st.sidebar.header("🎛️ Telematics Sliding Controls")

# Scenario Presets
preset = st.sidebar.selectbox(
    "Quick Scenario Presets",
    [
        "Custom Slider Controls",
        "Live Slope Optimization",
        "Maximum Range Extender",
        "Optimal Highway Cruise",
        "Steep Mountain Climb",
        "Downhill Descent",
        "Aggressive City Driving",
        "Stationary Idling"
    ]
)

# Preset default values (speed, rpm, accel, incline, payload, fuel_avail, temp, tire_psi)
defaults = {
    "Live Slope Optimization": (55.0, 1500,  0.0,  0.0, 2000.0,  60.0, 90.0, 35.0),
    "Maximum Range Extender":  (44.0, 1300,  0.0,  0.0,    0.0, 120.0, 90.0, 36.0),
    "Optimal Highway Cruise":  (80.0, 1600,  0.0,  0.0, 2000.0,  75.0, 88.0, 36.0),
    "Steep Mountain Climb":    (45.0, 2600,  0.8,  8.5, 6500.0,  50.0, 95.0, 34.0),
    "Downhill Descent":        (60.0, 1400, -0.5, -6.5, 3000.0,  40.0, 85.0, 35.0),
    "Aggressive City Driving": (55.0, 3200,  2.2,  1.0, 2500.0,  30.0, 90.0, 31.0),
    "Stationary Idling":       (0.0,  850,   0.0,  0.0, 4000.0,  65.0, 80.0, 35.0),
    "Custom Slider Controls":  (68.0, 1850,  0.2,  2.5, 3500.0,  55.0, 88.0, 33.0)
}
p_spd, p_rpm, p_acc, p_inc, p_load, p_fuel, p_temp, p_psi = defaults[preset]

# Sliders
st.sidebar.subheader("🚗 Powertrain & Driving")
speed = st.sidebar.slider("Speed (km/h)", 0.0, 140.0, float(p_spd), 1.0)
rpm = st.sidebar.slider("Engine RPM", 600, 5000, int(p_rpm), 50)
accel = st.sidebar.slider("Acceleration / Braking (m/s²)", -4.0, 4.0, float(p_acc), 0.1)

st.sidebar.subheader("⛰️ Road & Incline")

# If Live Slope Optimization is active, offer smartphone sensor sync
auto_live = False
if preset == "Live Slope Optimization":
    st.sidebar.markdown("### 🌐 IoT Telematics Ingestion")
    iot_source = st.sidebar.radio("Sensor Source", ["Cloud MQTT Broker", "Local Wi-Fi (Phyphox)"], horizontal=True)

    if iot_source == "Cloud MQTT Broker":
        st.sidebar.caption(f"**Broker:** `broker.hivemq.com` • **Topic:** `fleetfuel/telematics`")
        
        # Display MQTT status & last packet received
        mq_time = global_telemetry_store.last_time
        mq_inc = global_telemetry_store.incline
        mq_count = global_telemetry_store.packet_count
        if mq_time and mq_inc is not None:
            st.sidebar.success(f"📡 **Live MQTT Active:** Incline **{mq_inc:+.1f}°**\n\n*(Packet #{mq_count} at {mq_time})*")
        else:
            st.sidebar.info(f"🟢 **MQTT Connected** (`{MQTT_BROKER}`)\n\nWaiting for sensor packets on `{MQTT_TOPIC}`...")

        # Embedded In-Browser Smartphone Sensor Transmitter
        components.html("""
        <div style="background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); border-radius: 8px; padding: 10px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center;">
          <div style="font-size: 11px; font-weight: bold; color: #38bdf8; margin-bottom: 6px; letter-spacing: 0.5px;">📱 BROWSER MOTION TRANSMITTER</div>
          <button id="mqttSensorBtn" onclick="toggleMqttSensor()" style="background: #0284c7; color: white; border: none; padding: 7px 12px; border-radius: 5px; font-size: 12px; font-weight: bold; cursor: pointer; width: 100%;">
            Enable This Phone's Sensor
          </button>
          <div id="mqttSensorStatus" style="font-size: 11px; margin-top: 6px; color: #94a3b8;">Tap above to broadcast phone tilt via MQTT</div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js"></script>
        <script>
        let mqttClient = null;
        let active = false;
        let lastSent = 0;

        function toggleMqttSensor() {
          if (active) {
            active = false;
            document.getElementById("mqttSensorBtn").innerText = "Enable This Phone's Sensor";
            document.getElementById("mqttSensorStatus").innerText = "Status: Stopped";
            return;
          }
          if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
            DeviceOrientationEvent.requestPermission().then(response => {
              if (response === 'granted') startStreaming();
              else alert('Motion permission denied.');
            }).catch(e => startStreaming());
          } else {
            startStreaming();
          }
        }

        function startStreaming() {
          const clientId = "web_sender_" + Math.random().toString(16).substr(2, 8);
          mqttClient = new Paho.MQTT.Client("broker.hivemq.com", 8884, "/mqtt", clientId);
          mqttClient.connect({
            useSSL: true,
            onSuccess: function() {
              active = true;
              document.getElementById("mqttSensorBtn").innerText = "🛑 Stop Sensor";
              document.getElementById("mqttSensorStatus").innerHTML = "🟢 <b style='color:#22c55e;'>Connected!</b> Tilt phone to transmit.";
              window.addEventListener("deviceorientation", onOrientation);
            },
            onFailure: function(e) {
              document.getElementById("mqttSensorStatus").innerHTML = "⚠️ MQTT error: " + e.errorMessage;
            }
          });
        }

        function onOrientation(event) {
          if (!active) return;
          const now = Date.now();
          if (now - lastSent < 250) return;
          lastSent = now;
          let pitch = event.beta || 0;
          pitch = Math.max(-15, Math.min(15, pitch));
          document.getElementById("mqttSensorStatus").innerHTML = "📡 Incline: <b style='color:#38bdf8;'>" + pitch.toFixed(1) + "°</b>";
          const msg = new Paho.MQTT.Message(JSON.stringify({ incline: parseFloat(pitch.toFixed(1)) }));
          msg.destinationName = "fleetfuel/telematics";
          mqttClient.send(msg);
        }
        </script>
        """, height=110)

        auto_live = st.sidebar.checkbox("🔴 Auto-Refresh Dashboard", value=True, help="Refreshes UI every 1s when receiving live MQTT packets")

    else:
        # Local Wi-Fi Phyphox polling
        st.sidebar.info("📱 **Local Wi-Fi Mode (Localhost Only):** Direct polling from Phyphox app on same Wi-Fi.\n\n*(Note: On cloud links, use Cloud MQTT Broker)*")
        phone_url = st.sidebar.text_input("Phone URL (Phyphox)", "http://172.16.87.170:8080", help="Copy the URL shown on your phone's Phyphox screen")
        c_btn1, c_btn2 = st.sidebar.columns(2)
        with c_btn1:
            sync_phone = st.button("📲 Poll Phone")
        with c_btn2:
            auto_live = st.checkbox("🔴 Live Stream", value=False, help="Continuously poll phone tilt every 1s")

        if (sync_phone or auto_live) and phone_url:
            try:
                import requests
                clean_url = phone_url.rstrip("/")
                try:
                    requests.get(f"{clean_url}/control?cmd=start", timeout=0.8)
                except Exception:
                    pass
                res = requests.get(f"{clean_url}/get?tiltFlatUD&angle&tiltUprightUD", timeout=1.5).json()
                buf = res.get("buffer", {})
                val = None
                if "tiltFlatUD" in buf and len(buf["tiltFlatUD"].get("buffer", [])) > 0:
                    val = buf["tiltFlatUD"]["buffer"][0]
                elif "angle" in buf and len(buf["angle"].get("buffer", [])) > 0:
                    val = buf["angle"]["buffer"][0]
                elif "tiltUprightUD" in buf and len(buf["tiltUprightUD"].get("buffer", [])) > 0:
                    val = buf["tiltUprightUD"]["buffer"][0]

                if val is not None:
                    p_inc = round(float(np.clip(val, -15.0, 15.0)), 1)
                    st.session_state["live_slope_val"] = p_inc
                    st.sidebar.success(f"📡 Live Phone Tilt: **{p_inc}°**")
                else:
                    st.sidebar.warning("⚠️ No tilt buffer received. Ensure Phyphox is measuring.")
            except Exception:
                st.sidebar.warning("⚠️ Phone not reachable. Ensure dashboard is running locally on same Wi-Fi.")

# Determine current incline from IoT source or manual slider
if preset == "Live Slope Optimization" and iot_source == "Cloud MQTT Broker":
    if global_telemetry_store.packet_count > 0:
        incline = float(np.clip(global_telemetry_store.incline, -15.0, 15.0))
        st.sidebar.metric("Live Telemetry Incline", f"{incline:+.1f}°")
    else:
        incline = st.sidebar.slider("Incline Angle (°: -Downhill, +Uphill)", -15.0, 15.0, float(p_inc), 0.5)
    # Also update speed & RPM if provided by MQTT
    if global_telemetry_store.speed is not None:
        speed = float(global_telemetry_store.speed)
    if global_telemetry_store.rpm is not None:
        rpm = int(global_telemetry_store.rpm)
elif preset == "Live Slope Optimization" and iot_source == "Local Wi-Fi (Phyphox)":
    current_incline_val = float(st.session_state.get("live_slope_val", p_inc))
    incline = st.sidebar.slider("Incline Angle (°: -Downhill, +Uphill)", -15.0, 15.0, current_incline_val, 0.5)
else:
    incline = st.sidebar.slider("Incline Angle (°: -Downhill, +Uphill)", -15.0, 15.0, float(p_inc), 0.5)

st.sidebar.subheader("🛢️ Fuel & Vehicle State")
fuel_avail = st.sidebar.slider("Fuel in Tank (Liters)", 2.0, 120.0, float(p_fuel), 1.0)
payload = st.sidebar.slider("Cargo Payload (kg)", 0.0, 10000.0, float(p_load), 250.0)
temp = st.sidebar.slider("Engine Coolant Temp (°C)", 20.0, 115.0, float(p_temp), 1.0)
tire_psi = st.sidebar.slider("Tire Pressure (PSI)", 20.0, 42.0, float(p_psi), 1.0)
fuel_price = st.sidebar.number_input("Fuel Price (₹/L)", 50.0, 200.0, 95.0, 0.5)

# Calculate results based on current slider or live telemetry values
data = calculate_fuel_telematics(speed, rpm, accel, incline, payload, fuel_avail, temp, tire_psi, fuel_price)

# Prominent Main Page Live Ingestion Status Banner
if preset == "Live Slope Optimization" and iot_source == "Cloud MQTT Broker":
    if global_telemetry_store.packet_count > 0:
        st.success(f"⚡ **Live Phone Sensor Active:** Road Incline = **{incline:+.1f}°** *(Packet #{global_telemetry_store.packet_count} at {global_telemetry_store.last_time})*")
    else:
        st.info("💡 **Ready for Live Telemetry:** Tap **'Enable This Phone's Sensor'** above and tilt your device. Fuel consumption & range will recalculate in real-time.")

# Optimization recommendation banner for Live Slope
if preset == "Live Slope Optimization":
    if incline > 3.0:
        rec_spd = max(35.0, round(65.0 - (incline * 2.2)))
        st.warning(f"⛰️ **Steep Climb Detected ({incline:+.1f}°):** Downshift gear & reduce cruising speed to **{rec_spd} km/h** to minimize gravitational fuel penalty.")
    elif incline < -2.0:
        st.success(f"📉 **Downhill Assist Detected ({incline:+.1f}°):** Gravity provides tractive force. Maintain speed with zero throttle (fuel cut-off).")
    else:
        st.info(f"🛣️ **Level Terrain ({incline:+.1f}°):** Optimal steady cruise speed is **65–75 km/h**.")

# ==============================================================================
# 4. TOP KPI METRIC CARDS
# ==============================================================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Actual Fuel Rate", f"{data['actual_lh']} L/h", f"{data['dev_pct']:+}% vs baseline", delta_color="inverse")
c2.metric("Expected Baseline", f"{data['expected_lh']} L/h", "Target")
c3.metric("Fuel Economy", f"{data['km_per_l']} km/L", f"{data['l_per_100km']} L/100km", delta_color="off")
c4.metric("Estimated Range", f"{data['remaining_range_km']} km", f"~{data['remaining_hours']} hrs endurance", delta_color="off")
c5.metric("Excess Cost Impact", f"₹{data['waste_cost_per_hr']} /hr", f"{data['excess_fuel_lh']:+} L/h", delta_color="inverse")

st.divider()

# ==============================================================================
# 5. SIMULTANEOUS INTERACTIVE GRAPHS (TABS)
# ==============================================================================
tab1, tab2, tab3 = st.tabs([
    "📈 Operating Curve & Live Point",
    "🔍 Root-Cause Inefficiency (SHAP)",
    "🛢️ Fuel Depletion & Range Forecast"
])

# --- TAB 1: FUEL CONSUMPTION VS SPEED OPERATING CURVE ---
with tab1:
    col_plot, col_gauge = st.columns([7, 3])
    
    with col_plot:
        # Generate speed sweep curve (5 to 130 km/h) under current conditions
        speeds = np.linspace(5, 130, 40)
        curve_actual = [calculate_fuel_telematics(s, rpm, 0.0, incline, payload, fuel_avail, temp, tire_psi)["actual_lh"] for s in speeds]
        curve_expected = [calculate_fuel_telematics(s, rpm, 0.0, 0.0, payload, fuel_avail, temp, tire_psi)["expected_lh"] for s in speeds]

        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(x=speeds, y=curve_expected, mode='lines', name='Expected Baseline', line=dict(dash='dash', color='#38bdf8', width=2)))
        fig_curve.add_trace(go.Scatter(x=speeds, y=curve_actual, mode='lines', name='Current Condition Curve', line=dict(color='#818cf8', width=3)))
        fig_curve.add_trace(go.Scatter(
            x=[speed], y=[data['actual_lh']], mode='markers+text', name='Current Point',
            text=[f"Current: {data['actual_lh']} L/h"], textposition="top center",
            marker=dict(size=14, color="#ef4444" if data['dev_pct'] > 15 else "#10b981", symbol="diamond")
        ))
        fig_curve.update_layout(
            title=f"Fuel Rate vs Vehicle Speed (Incline: {incline}°, Payload: {payload} kg)",
            xaxis_title="Speed (km/h)", yaxis_title="Fuel Rate (L/h)", height=420
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    with col_gauge:
        # Power demand gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=data["power_kw"],
            title={'text': "Engine Power Demand (kW)"},
            gauge={
                'axis': {'range': [0, 180]},
                'bar': {'color': "#38bdf8"},
                'steps': [
                    {'range': [0, 60], 'color': "rgba(16, 185, 129, 0.3)"},
                    {'range': [60, 120], 'color': "rgba(245, 158, 11, 0.3)"},
                    {'range': [120, 180], 'color': "rgba(239, 68, 68, 0.3)"}
                ]
            }
        ))
        fig_gauge.update_layout(height=340)
        st.plotly_chart(fig_gauge, use_container_width=True)
        terrain = "Ascent (Uphill)" if incline > 0 else ("Descent (Downhill)" if incline < 0 else "Flat Ground")
        st.info(f"**Terrain Profile:** {terrain} ({abs(incline)}°)")

# --- TAB 2: INEFFICIENCY EXPLAINABILITY (SHAP BREAKDOWN) ---
with tab2:
    st.subheader("Inefficiency Decomposition (Why Consumption Changed)")
    st.caption("SHAP-style attribution breaking down exact contributors to fuel burn.")

    df_factors = pd.DataFrame({
        "Contributor": list(data["factors"].keys()),
        "Fuel Rate (L/h)": list(data["factors"].values())
    }).sort_values(by="Fuel Rate (L/h)", ascending=True)

    fig_shap = go.Figure(go.Bar(
        x=df_factors["Fuel Rate (L/h)"],
        y=df_factors["Contributor"],
        orientation='h',
        marker=dict(color=df_factors["Fuel Rate (L/h)"], colorscale='Blues'),
        text=df_factors["Fuel Rate (L/h)"].apply(lambda x: f"{x} L/h"),
        textposition='outside'
    ))
    fig_shap.update_layout(xaxis_title="Fuel Contribution (L/h)", height=360)
    
    col_b, col_rec = st.columns([6, 4])
    with col_b:
        st.plotly_chart(fig_shap, use_container_width=True)
    with col_rec:
        st.markdown("### 💡 Recommended Actions")
        if incline > 5:
            st.warning(f"⛰️ **Steep Climb:** Overcoming {incline}° incline adds substantial gravity load.")
        if accel > 1.5:
            st.error(f"⚡ **Harsh Acceleration:** High throttle rate ({accel} m/s²) surges fuel demand.")
        if rpm > 2500 and speed < 80:
            st.warning(f"⚙️ **High RPM:** Shift to a higher gear to reduce engine friction.")
        if tire_psi < 30:
            st.warning(f"🔘 **Low Tire Pressure:** Inflate tires to 35 PSI to lower rolling resistance.")
        if speed == 0:
            st.info("🛑 **Idling Detected:** Engine is on while stationary; consumes ~1.2 L/h.")

# --- TAB 3: FUEL DEPLETION & RANGE FORECAST ---
with tab3:
    st.subheader("Fuel Depletion Horizon")
    st.caption("Shows fuel remaining in tank over travel distance at current driving rate.")

    trip_distances = np.linspace(0, max(50, min(500, data["remaining_range_km"] * 1.2)), 40)
    fuel_curve = [max(0.0, fuel_avail - (d / data["km_per_l"])) if data["km_per_l"] > 0 else fuel_avail for d in trip_distances]

    fig_dep = go.Figure()
    fig_dep.add_trace(go.Scatter(x=trip_distances, y=fuel_curve, mode='lines', fill='tozeroy', name='Remaining Fuel (L)', line=dict(color='#38bdf8', width=3)))
    fig_dep.add_hline(y=10.0, line_dash="dot", line_color="#ef4444", annotation_text="Critical Reserve (10 L)")
    fig_dep.update_layout(xaxis_title="Distance Traveled (km)", yaxis_title="Fuel Level (Liters)", height=400)
    st.plotly_chart(fig_dep, use_container_width=True)

st.caption("FleetFuel AI Telematics System • Simple, Explainable Vehicle Fuel Intelligence")

# Auto-Stream Continuous Polling (1 second intervals)
if preset == "Live Slope Optimization" and auto_live:
    import time
    time.sleep(1.0)
    st.rerun()
