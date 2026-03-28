"""
services/voltage-regulator/app.py
===================================
Dedicated voltage stability service.
Manages tap changers on transformers, capacitor banks in zones,
reactive power compensation.

CAN BREAK:
  1. Tap Changer Runaway
  2. Reactive Power Collapse
  3. Voltage Profile Violation
"""

import os
import sys
import time
import threading
import random
from flask import Flask, request, jsonify, Response
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services.shared.logger import setup_logger, write_simulation_log

app = Flask(__name__)
SERVICE_NAME = "voltage-regulator"
PORT = 5009
START_TIME = time.time()
logger = setup_logger(SERVICE_NAME)

ZONE_PORTS = {"north": 5003, "south": 5004, "east": 5005, "west": 5006, "central": 5007}
ZONE_HOSTS = {
    "north": os.getenv("ZONE_NORTH_HOST", "localhost"),
    "south": os.getenv("ZONE_SOUTH_HOST", "localhost"),
    "east": os.getenv("ZONE_EAST_HOST", "localhost"),
    "west": os.getenv("ZONE_WEST_HOST", "localhost"),
    "central": os.getenv("ZONE_CENTRAL_HOST", "localhost"),
}


def zone_url(zone: str, path: str) -> str:
    return f"http://{ZONE_HOSTS[zone]}:{ZONE_PORTS[zone]}{path}"

state_lock = threading.Lock()
state = {
    "grid_voltage_avg_v":         229.5,
    "grid_voltage_min_v":         226.8,
    "grid_voltage_max_v":         232.1,
    "grid_power_factor_avg":      0.94,
    "tap_changes_per_hour":       1.2,
    "capacitor_banks_active_count": 0,
    "reactive_power_total_kvar":  620.0,
    "voltage_violations_count":   0,
    "tap_changer_locked":         False,
    "total_reactive_compensation_kvar": 0,
    "zone_voltage_profiles": {
        zone: {
            "avg_v":            round(random.uniform(228, 231), 1),
            "min_v":            round(random.uniform(225, 228), 1),
            "max_v":            round(random.uniform(231, 234), 1),
            "tap_position":     0,
            "capacitor_bank_active": False,
            "reactive_power_kvar":   round(random.uniform(80, 200), 1),
            "power_factor":     round(random.uniform(0.91, 0.97), 3),
        }
        for zone in ["north", "south", "east", "west", "central"]
    },
    "voltage_violations": [],
    "_tap_change_events_last_hour": 0,
    "_last_hour_reset": time.time(),
    "active_fault": None,
}


def poll_and_regulate():
    """Poll zones every 5s, compute voltage profile, take corrective action."""
    while True:
        try:
            voltages = []
            violations = []
            total_reactive = 0
            power_factors = []

            for zone, port in ZONE_PORTS.items():
                try:
                    r = requests.get(zone_url(zone, "/status"), timeout=2)
                    if r.status_code == 200:
                        d = r.json()
                        v_avg = d.get("voltage_avg_v", 230)
                        voltages.append(v_avg)
                        pf = d.get("power_factor", 0.94)
                        power_factors.append(pf)
                        total_reactive += d.get("reactive_power_kvar", 100)

                        # Check violation
                        if v_avg < 210 or v_avg > 244:
                            violations.append({
                                "zone": zone,
                                "voltage_v": v_avg,
                                "type": "low" if v_avg < 210 else "high",
                            })

                        # Update per-zone profile
                        with state_lock:
                            zp = state["zone_voltage_profiles"][zone]
                            zp["avg_v"] = round(v_avg, 1)
                            zp["min_v"] = round(v_avg - random.uniform(1, 4), 1)
                            zp["max_v"] = round(v_avg + random.uniform(1, 4), 1)
                            zp["reactive_power_kvar"] = round(
                                d.get("reactive_power_kvar", 100), 1)
                            zp["power_factor"] = round(pf, 3)
                            zp["capacitor_bank_active"] = d.get("capacitor_bank_active", False)

                            # Autonomous tap correction (if not locked)
                            if not state["tap_changer_locked"]:
                                if v_avg < 225 and zp["tap_position"] < 4:
                                    zp["tap_position"] += 1
                                    state["_tap_change_events_last_hour"] += 1
                                    logger.info(f"[TAP] {zone}: tap raised to {zp['tap_position']}")
                                    # Notify zone
                                    try:
                                        requests.post(zone_url(zone, "/tap-change"), 
                                                      json={"position": zp["tap_position"]}, timeout=1)
                                    except: pass
                                elif v_avg > 233 and zp["tap_position"] > -4:
                                    zp["tap_position"] -= 1
                                    state["_tap_change_events_last_hour"] += 1
                                    logger.info(f"[TAP] {zone}: tap lowered to {zp['tap_position']}")
                                    # Notify zone
                                    try:
                                        requests.post(zone_url(zone, "/tap-change"), 
                                                      json={"position": zp["tap_position"]}, timeout=1)
                                    except: pass

                except Exception:
                    pass

            with state_lock:
                # Reset hourly tap counter
                if time.time() - state["_last_hour_reset"] > 3600:
                    state["tap_changes_per_hour"] = state["_tap_change_events_last_hour"]
                    state["_tap_change_events_last_hour"] = 0
                    state["_last_hour_reset"] = time.time()
                else:
                    # Estimate rate
                    elapsed_hrs = (time.time() - state["_last_hour_reset"]) / 3600
                    if elapsed_hrs > 0:
                        state["tap_changes_per_hour"] = round(
                            state["_tap_change_events_last_hour"] / elapsed_hrs, 1)

                if voltages:
                    state["grid_voltage_avg_v"] = round(sum(voltages) / len(voltages), 2)
                    state["grid_voltage_min_v"] = round(min(voltages), 2)
                    state["grid_voltage_max_v"] = round(max(voltages), 2)
                if power_factors:
                    state["grid_power_factor_avg"] = round(
                        sum(power_factors) / len(power_factors), 3)
                state["reactive_power_total_kvar"] = round(total_reactive, 1)
                state["voltage_violations_count"] = len(violations)
                state["voltage_violations"] = violations

                # Active capacitor banks count
                state["capacitor_banks_active_count"] = sum(
                    1 for zp in state["zone_voltage_profiles"].values()
                    if zp.get("capacitor_bank_active")
                )

        except Exception as e:
            logger.error(f"[POLL-ERROR] {e}")
        time.sleep(5)


# ─── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "online", "service": SERVICE_NAME,
                    "uptime_s": round(time.time() - START_TIME, 1)})


@app.route("/status")
def status():
    with state_lock:
        return jsonify(dict(state))


@app.route("/metrics")
def prom_metrics():
    with state_lock:
        s = dict(state)
    lines = [
        '# HELP vr_grid_voltage_avg_v Average grid voltage',
        '# TYPE vr_grid_voltage_avg_v gauge',
        f'vr_grid_voltage_avg_v {s["grid_voltage_avg_v"]}',
        '# HELP vr_grid_power_factor_avg Average power factor',
        '# TYPE vr_grid_power_factor_avg gauge',
        f'vr_grid_power_factor_avg {s["grid_power_factor_avg"]}',
        '# HELP vr_voltage_violations_count Voltage violations detected',
        '# TYPE vr_voltage_violations_count gauge',
        f'vr_voltage_violations_count {s["voltage_violations_count"]}',
        '# HELP vr_tap_changes_per_hour Tap changes per hour',
        '# TYPE vr_tap_changes_per_hour gauge',
        f'vr_tap_changes_per_hour {s["tap_changes_per_hour"]}',
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/tap-changer/lock", methods=["POST"])
def lock_tap_changer():
    data = request.get_json(force=True) or {}
    zone = data.get("zone")
    with state_lock:
        state["tap_changer_locked"] = True
    logger.info(f"[TAP-LOCK] Tap changer locked for zone={zone}")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Tap changer locked zone={zone}")
    return jsonify({"tap_changer_locked": True, "zone": zone})


@app.route("/tap-changer/unlock", methods=["POST"])
def unlock_tap_changer():
    with state_lock:
        state["tap_changer_locked"] = False
    return jsonify({"tap_changer_locked": False})


@app.route("/capacitor-bank/activate", methods=["POST"])
def activate_capacitor():
    data = request.get_json(force=True) or {}
    zone = data.get("zone")
    with state_lock:
        if zone and zone in state["zone_voltage_profiles"]:
            state["zone_voltage_profiles"][zone]["capacitor_bank_active"] = True
            state["zone_voltage_profiles"][zone]["reactive_power_kvar"] *= 0.6
            state["capacitor_banks_active_count"] += 1
    # Also activate on the zone service
    if zone and zone in ZONE_PORTS:
        try:
            requests.post(zone_url(zone, "/capacitor-bank/activate"),
                          timeout=2)
        except Exception:
            pass
    logger.info(f"[CAPACITOR] Bank activated for zone={zone}")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Capacitor bank activated zone={zone}")
    return jsonify({"capacitor_bank_active": True, "zone": zone})


@app.route("/capacitor-bank/deactivate", methods=["POST"])
def deactivate_capacitor():
    data = request.get_json(force=True) or {}
    zone = data.get("zone")
    with state_lock:
        if zone and zone in state["zone_voltage_profiles"]:
            state["zone_voltage_profiles"][zone]["capacitor_bank_active"] = False
            state["capacitor_banks_active_count"] = max(0, state["capacitor_banks_active_count"] - 1)
        elif not zone:
            # Deactivate all
            for zp in state["zone_voltage_profiles"].values():
                zp["capacitor_bank_active"] = False
            state["capacitor_banks_active_count"] = 0
    logger.info(f"[CAPACITOR] Bank deactivated for zone={zone}")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Capacitor bank deactivated zone={zone}")
    return jsonify({"capacitor_bank_active": False, "zone": zone})


@app.route("/reactive-compensation/maximum", methods=["POST"])
def max_reactive_compensation():
    data = request.get_json(force=True) or {}
    zone = data.get("zone")
    with state_lock:
        state["total_reactive_compensation_kvar"] = 1000
        state["capacitor_banks_active_count"] = 5
        if zone and zone in state["zone_voltage_profiles"]:
            state["zone_voltage_profiles"][zone]["capacitor_bank_active"] = True
            state["zone_voltage_profiles"][zone]["power_factor"] = min(
                0.98, state["zone_voltage_profiles"][zone]["power_factor"] + 0.06)
        # Activate all capacitor banks
        for zname in state["zone_voltage_profiles"]:
            state["zone_voltage_profiles"][zname]["capacitor_bank_active"] = True
    logger.info(f"[REACTIVE-MAX] Maximum reactive compensation activated")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         "Maximum reactive compensation activated")
    return jsonify({"compensation_kvar": 1000, "all_banks_active": True})


@app.route("/demo/inject", methods=["POST"])
def demo_inject():
    data = request.get_json(force=True) or {}
    fault_type = data.get("type", "voltage_instability")

    with state_lock:
        state["active_fault"] = fault_type

        if fault_type in ("voltage_instability", "voltage_overload"):
            zone = data.get("zone", "central")
            v = data.get("voltage_v", None)
            if fault_type == "voltage_overload":
                # High voltage surge across grid
                v = v or random.uniform(244, 258)
                state["grid_voltage_avg_v"] = v
                state["grid_voltage_max_v"] = v + 2
                state["voltage_violations_count"] = random.randint(3, 6)
                for zname, zp in state["zone_voltage_profiles"].items():
                    zp["avg_v"] = random.uniform(244, 255)
                    zp["max_v"] = zp["avg_v"] + 2
            else:
                # Low voltage / tap changer hunting
                v = v or random.uniform(200, 213)
                if zone in state["zone_voltage_profiles"]:
                    state["zone_voltage_profiles"][zone]["avg_v"] = v
                    state["zone_voltage_profiles"][zone]["min_v"] = v - 5
                state["grid_voltage_avg_v"] = v + 3
                state["grid_voltage_min_v"] = v
                if data.get("tap_oscillation"):
                    state["tap_changes_per_hour"] = random.uniform(25, 60)
                    state["_tap_change_events_last_hour"] = int(
                        state["tap_changes_per_hour"] * 0.1)

        elif fault_type == "reactive_power_collapse":
            state["grid_power_factor_avg"] = data.get("power_factor", random.uniform(0.65, 0.78))
            state["voltage_violations_count"] = random.randint(3, 6)
            state["reactive_power_total_kvar"] = random.uniform(1200, 1800)
            for zp in state["zone_voltage_profiles"].values():
                zp["reactive_power_kvar"] = random.uniform(800, 1400)
                zp["power_factor"] = random.uniform(0.67, 0.78)

        elif fault_type == "voltage_profile_violation":
            zone = data.get("zone", "east")
            if zone in state["zone_voltage_profiles"]:
                state["zone_voltage_profiles"][zone]["min_v"] = random.uniform(200, 208)
                state["zone_voltage_profiles"][zone]["avg_v"] = random.uniform(205, 212)
            state["voltage_violations_count"] += 1

    logger.warning(f"[INJECT] {fault_type} injected into voltage-regulator")
    write_simulation_log(SERVICE_NAME, "INJECT",
                         f"{fault_type} injected into voltage-regulator")
    return jsonify({"injected": True, "fault_type": fault_type,
                    "component": "voltage-regulator"})


@app.route("/demo/reset")
def demo_reset():
    with state_lock:
        state["tap_changer_locked"] = False
        state["voltage_violations_count"] = 0
        state["voltage_violations"] = []
        state["grid_voltage_avg_v"] = random.uniform(228, 231)
        state["grid_voltage_min_v"] = random.uniform(225, 229)
        state["grid_power_factor_avg"] = random.uniform(0.91, 0.97)
        state["tap_changes_per_hour"] = random.uniform(0, 3)
        state["capacitor_banks_active_count"] = 0
        state["active_fault"] = None
        for zp in state["zone_voltage_profiles"].values():
            zp["capacitor_bank_active"] = False
            zp["tap_position"] = 0
            zp["avg_v"] = random.uniform(228, 231)
            zp["power_factor"] = random.uniform(0.91, 0.97)
    return jsonify({"reset": True})


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {PORT}")
    threading.Thread(target=poll_and_regulate, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
