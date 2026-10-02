#!/usr/bin/env python3
"""IoT pipeline demo: register device, ingest data, process stream, detect anomaly, generate alert."""

import json
import random
import statistics
import time
import uuid
from datetime import datetime, timezone


# ── 1. Register device ────────────────────────────────────────────────────────
def register_device(device_type: str, location: str) -> dict:
    device = {
        "device_id": str(uuid.uuid4())[:8],
        "type": device_type,
        "location": location,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    print(f"[1] Registered device: {device['device_id']} ({device_type}) at {location}")
    return device


# ── 2. Ingest data ─────────────────────────────────────────────────────────────
def ingest_data(device: dict, num_readings: int = 20) -> list[dict]:
    readings = []
    base_temp = 22.0
    for i in range(num_readings):
        reading = {
            "device_id": device["device_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": round(base_temp + random.gauss(0, 1.5), 2),
            "humidity": round(50 + random.gauss(0, 5), 2),
        }
        readings.append(reading)
    print(f"[2] Ingested {len(readings)} readings from device {device['device_id']}")
    return readings


# ── 3. Process stream ──────────────────────────────────────────────────────────
def process_stream(readings: list[dict]) -> dict:
    temps = [r["temperature"] for r in readings]
    humidities = [r["humidity"] for r in readings]
    stats = {
        "count": len(readings),
        "avg_temperature": round(statistics.mean(temps), 2),
        "avg_humidity": round(statistics.mean(humidities), 2),
        "min_temperature": round(min(temps), 2),
        "max_temperature": round(max(temps), 2),
    }
    print(f"[3] Stream processed: {stats['count']} points, "
          f"avg_temp={stats['avg_temperature']}°C, "
          f"range=[{stats['min_temperature']}, {stats['max_temperature']}]°C")
    return stats


# ── 4. Detect anomaly ──────────────────────────────────────────────────────────
def detect_anomaly(readings: list[dict], threshold_std: float = 2.0) -> list[dict]:
    temps = [r["temperature"] for r in readings]
    mean = statistics.mean(temps)
    stdev = statistics.stdev(temps) if len(temps) > 1 else 0

    anomalies = []
    for r in readings:
        if stdev > 0 and abs(r["temperature"] - mean) > threshold_std * stdev:
            anomalies.append({
                "timestamp": r["timestamp"],
                "temperature": r["temperature"],
                "deviation": round(r["temperature"] - mean, 2),
            })

    # Inject a synthetic anomaly for demo purposes
    if not anomalies:
        spike = readings[-1].copy()
        spike["temperature"] = round(mean + threshold_std * stdev + 3.0, 2)
        spike["timestamp"] = datetime.now(timezone.utc).isoformat()
        anomalies.append({
            "timestamp": spike["timestamp"],
            "temperature": spike["temperature"],
            "deviation": round(spike["temperature"] - mean, 2),
        })

    print(f"[4] Anomaly detection: {len(anomalies)} anomaly/ies found "
          f"(threshold: {threshold_std}σ from mean={round(mean, 2)}°C)")
    for a in anomalies:
        print(f"    → {a['timestamp']}: {a['temperature']}°C (deviation: {a['deviation']}°C)")
    return anomalies


# ── 5. Generate alert ──────────────────────────────────────────────────────────
def generate_alert(device: dict, anomalies: list[dict], stats: dict) -> dict:
    alert = {
        "alert_id": str(uuid.uuid4())[:8],
        "device_id": device["device_id"],
        "location": device["location"],
        "severity": "high" if len(anomalies) > 1 else "medium",
        "message": (f"Temperature anomaly detected at {device['location']}: "
                    f"{len(anomalies)} reading(s) outside normal range."),
        "anomalies": anomalies,
        "context": {
            "avg_temperature": stats["avg_temperature"],
            "normal_range": [stats["min_temperature"], stats["max_temperature"]],
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"[5] Alert generated: {alert['alert_id']} | severity={alert['severity']}")
    print(f"    Message: {alert['message']}")
    return alert


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("IoT Pipeline Demo")
    print("=" * 60)

    device = register_device("temperature_sensor", "Warehouse-A")
    readings = ingest_data(device, num_readings=20)
    stats = process_stream(readings)
    anomalies = detect_anomaly(readings, threshold_std=2.0)
    alert = generate_alert(device, anomalies, stats)

    print("\n" + "=" * 60)
    print("Alert JSON:")
    print(json.dumps(alert, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
