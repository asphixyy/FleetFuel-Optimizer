"""
FleetFuel AI - Standalone Vehicle IoT Simulator
Publishes live vehicle telemetry packets to the public MQTT broker.
Usage:
    python simulate_iot_truck.py
"""

import time
import json
import math
import random
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "fleetfuel/telematics"

print("=" * 60)
print("⚡ FLEETFUEL AI - VEHICLE IoT TELEMETRICS TRANSMITTER")
print(f"Connecting to Cloud Broker: {BROKER}:{PORT}")
print(f"Publishing to Topic: {TOPIC}")
print("=" * 60)

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None,
    client_id=f"truck_sim_{int(time.time())}"
)

client.connect(BROKER, PORT, 60)
client.loop_start()

t = 0.0
try:
    while True:
        # Simulate realistic mountain / highway driving profile
        incline = round(math.sin(t * 0.15) * 8.5, 1)          # Incline oscillates between -8.5° and +8.5°
        speed = round(max(30.0, 70.0 - (incline * 2.5)), 1)   # Slows down uphill, speeds up downhill
        rpm = int(1400 + (speed * 12) + (max(0, incline) * 80)) # Higher RPM when climbing
        accel = round(math.cos(t * 0.2) * 1.2, 2)

        packet = {
            "vehicle_id": "TRUCK-01",
            "incline": incline,
            "speed": speed,
            "rpm": rpm,
            "accel": accel,
            "timestamp": time.strftime("%H:%M:%S")
        }

        payload = json.dumps(packet)
        client.publish(TOPIC, payload)
        print(f"📡 [{packet['timestamp']}] Sent Telematics: Incline={incline:+.1f}° | Speed={speed:.1f} km/h | RPM={rpm}")

        t += 1.0
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nSimulation stopped.")
    client.loop_stop()
    client.disconnect()
