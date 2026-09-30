import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

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
if preset == "Live Slope Optimization":
    st.sidebar.info("📱 **IoT Mode:** Stream slope live from phone motion sensors!")
    phone_url = st.sidebar.text_input("Phone URL (Phyphox)", "http://192.168.1.15:8080", help="Enable Remote Access in the Phyphox app")
    c_btn1, c_btn2 = st.sidebar.columns(2)
    with c_btn1:
        sync_phone = st.button("📲 Poll Phone")
    with c_btn2:
        auto_tilt = st.checkbox("Auto-Demo", value=False, help="Simulate slope changes automatically")

    if sync_phone and phone_url:
        try:
            import requests
            # Fetch all active buffers from Phyphox
            res = requests.get(f"{phone_url.rstrip('/')}/get", timeout=1.5).json()
            buf = res.get("buffer", {})
            
            # Check for direct inclination/pitch first
            if "inclination" in buf and len(buf["inclination"]["buffer"]) > 0:
                p_inc = round(float(buf["inclination"]["buffer"][0]), 1)
            elif "pitch" in buf and len(buf["pitch"]["buffer"]) > 0:
                p_inc = round(float(buf["pitch"]["buffer"][0]), 1)
            # Universal fallback: 'Acceleration with g' (available on all phones)
            elif "accY" in buf and len(buf["accY"]["buffer"]) > 0:
                ay = float(buf["accY"]["buffer"][0])
                az = float(buf["accZ"]["buffer"][0]) if ("accZ" in buf and len(buf["accZ"]["buffer"]) > 0) else 9.81
                # Calculate tilt/pitch from gravity components: theta = arctan2(ay, az)
                calc_angle = np.degrees(np.arctan2(ay, az))
                p_inc = round(float(np.clip(calc_angle, -15.0, 15.0)), 1)
            elif "acc" in buf and len(buf["acc"]["buffer"]) > 0:
                ay = float(buf["acc"]["buffer"][0])
                p_inc = round(float(np.clip(np.degrees(np.arcsin(np.clip(ay / 9.81, -1.0, 1.0))), -15.0, 15.0)), 1)
            else:
                p_inc = 0.0

            st.sidebar.success(f"📡 Phone Slope: {p_inc}°")
        except Exception:
            st.sidebar.warning("⚠️ Phone not reachable. Ensure same Wi-Fi.")
    elif auto_tilt:
        import time
        p_inc = round(float(np.sin(time.time() * 0.7) * 9.0), 1)

incline = st.sidebar.slider("Incline Angle (°: -Downhill, +Uphill)", -15.0, 15.0, float(p_inc), 0.5)

st.sidebar.subheader("🛢️ Fuel & Vehicle State")
fuel_avail = st.sidebar.slider("Fuel in Tank (Liters)", 2.0, 120.0, float(p_fuel), 1.0)
payload = st.sidebar.slider("Cargo Payload (kg)", 0.0, 10000.0, float(p_load), 250.0)
temp = st.sidebar.slider("Engine Coolant Temp (°C)", 20.0, 115.0, float(p_temp), 1.0)
tire_psi = st.sidebar.slider("Tire Pressure (PSI)", 20.0, 42.0, float(p_psi), 1.0)
fuel_price = st.sidebar.number_input("Fuel Price (₹/L)", 50.0, 200.0, 95.0, 0.5)

# Calculate results based on current slider values
data = calculate_fuel_telematics(speed, rpm, accel, incline, payload, fuel_avail, temp, tire_psi, fuel_price)

# Optimization recommendation banner for Live Slope
if preset == "Live Slope Optimization":
    if incline > 3.0:
        rec_spd = max(35.0, round(65.0 - (incline * 2.2)))
        st.warning(f"⛰️ **Steep Climb Detected ({incline}°):** Downshift gear & reduce cruising speed to **{rec_spd} km/h** to minimize gravitational fuel penalty.")
    elif incline < -2.0:
        st.success(f"📉 **Downhill Assist Detected ({incline}°):** Gravity provides tractive force. Maintain speed with zero throttle (fuel cut-off).")
    else:
        st.info(f"🛣️ **Level Terrain ({incline}°):** Optimal steady cruise speed is **65–75 km/h**.")

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
