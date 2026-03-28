"""
services/zone-north/app.py  (template for all 5 zone services)
===============================================================
Each zone service imports its own config.py to differentiate.

CAN BREAK:
  1. Feeder Overload
  2. Substation Trip
  3. Voltage Sag (brownout)
  4. Frequency Deviation
"""

import os
import sys
import time
import threading
import random
import math
from flask import Flask, request, jsonify, Response
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services.shared.logger import setup_logger, write_simulation_log

# ─── Load zone-specific config ─────────────────────────────────────────────────
# Each zone directory has its own config.py
_zone_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _zone_dir)
import config as ZONE_CFG

app = Flask(__name__)
SERVICE_NAME = f"zone-{ZONE_CFG.ZONE_NAME}"
PORT = ZONE_CFG.PORT
START_TIME = time.time()
logger = setup_logger(SERVICE_NAME)
GRID_CONTROLLER_HOST = os.getenv("GRID_CONTROLLER_HOST", "localhost")

# ─── State ─────────────────────────────────────────────────────────────────────
state_lock = threading.Lock()

def _init_sectors():
    sectors = {}
    for i in range(1, ZONE_CFG.NUM_SECTORS + 1):
        capacity = ZONE_CFG.PEAK_LOAD_MW / ZONE_CFG.NUM_SECTORS * random.uniform(0.9, 1.1)
        load_pct = random.uniform(50, 75)
        sectors[f"sector-{i}"] = {
            "load_mw":           round(capacity * load_pct / 100, 1),
            "feeder_capacity_mw": round(capacity, 1),
            "voltage_v":         round(random.uniform(226, 232), 1),
            "status":            "normal",
        }
    return sectors

state = {
    "zone":               ZONE_CFG.ZONE_NAME,
    "peak_load_mw":      ZONE_CFG.PEAK_LOAD_MW,
    "current_load_mw":   ZONE_CFG.PEAK_LOAD_MW * random.uniform(0.55, 0.72),
    "load_percent":      0,
    "frequency_hz":      50.0,
    "voltage_avg_v":     random.uniform(228, 231),
    "power_factor":      random.uniform(0.91, 0.96),
    "reactive_power_kvar": random.uniform(100, 250),
    "feeder_status":     {f"feeder-{i}": "healthy" for i in range(1, ZONE_CFG.NUM_FEEDERS + 1)},
    "capacitor_bank_active": False,
    "substation_status": "healthy",
    "relay_status":      "armed",
    "sectors":           _init_sectors(),
    "active_events":     0,
    "tap_v_offset":      0,
}
state["load_percent"] = round(state["current_load_mw"] / state["peak_load_mw"] * 100, 1)


# ─── Background simulation ──────────────────────────────────────────────────────

def simulate():
    while True:
        with state_lock:
            # Skip simulation if restarting
            if state.get("_is_restarting"):
                continue

            # Natural load drift following time-of-day pattern (simplified)
            hour_factor = 0.65 + 0.15 * math.sin(time.time() / 3600) 
            target_load = ZONE_CFG.PEAK_LOAD_MW * hour_factor * random.uniform(0.85, 0.95)
            drift = (target_load - state["current_load_mw"]) * 0.05 + random.gauss(0, 8)
            new_load = max(100, min(ZONE_CFG.PEAK_LOAD_MW * 1.1,
                                   state["current_load_mw"] + drift))
            state["current_load_mw"] = round(new_load, 1)
            state["load_percent"] = round(new_load / state["peak_load_mw"] * 100, 1)

            # Frequency: deviates with load imbalance
            load_imbalance = state["load_percent"] - 65  # 65% is nominal balance point
            freq_drift = -load_imbalance * 0.003 + random.gauss(0, 0.02)
            state["frequency_hz"] = round(
                max(49.0, min(51.0, state["frequency_hz"] + freq_drift)), 3)

            # Voltage: droops with load, boosted by caps and taps
            base_v = 230
            load_factor = state["load_percent"] / 100
            cap_boost = 3.0 if state["capacitor_bank_active"] else 0
            tap_boost = state["tap_v_offset"]
            state["voltage_avg_v"] = round(
                base_v - load_factor ** 1.5 * 12 + cap_boost + tap_boost + random.gauss(0, 0.3), 2)

            # Reactive power
            reactive = state["reactive_power_kvar"] + random.gauss(0, 5)
            state["reactive_power_kvar"] = round(max(0, reactive), 1)

            # Power factor
            state["power_factor"] = round(max(0.7, min(0.99,
                state["power_factor"] + random.gauss(0, 0.003))), 3)

            # Sector loads
            for sname, sector in state["sectors"].items():
                if sector["status"] == "normal":
                    s_drift = random.gauss(0, 3)
                    sector["load_mw"] = round(
                        max(10, min(sector["feeder_capacity_mw"] * 1.3,
                                   sector["load_mw"] + s_drift)), 1)
                    sector["voltage_v"] = round(state["voltage_avg_v"]
                        + random.gauss(0, 0.5), 1)

            # Check for alerts (silencing frequency deviation as requested)
            if state["load_percent"] > 90:
                state["substation_status"] = "stressed"
                _alert("critical",
                       f"Zone {ZONE_CFG.ZONE_NAME} overloaded at {state['load_percent']:.1f}%")
            elif state["load_percent"] > 80:
                state["active_events"] = max(state["active_events"], 1)

        time.sleep(5)


def _alert(severity, message):
    """Non-blocking alert to grid controller."""
    try:
        requests.post(f"http://{GRID_CONTROLLER_HOST}:5001/alert", json={
            "severity": severity,
            "service": SERVICE_NAME,
            "zone": ZONE_CFG.ZONE_NAME,
            "message": message,
        }, timeout=1)
    except Exception:
        pass


# ─── Routes ────────────────────────────────────────────────────────────────────

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
    zone = ZONE_CFG.ZONE_NAME
    lines = [
        f'# HELP zone_load_percent Zone load percentage',
        f'# TYPE zone_load_percent gauge',
        f'zone_load_percent{{zone="{zone}"}} {s["load_percent"]}',
        f'# HELP zone_frequency_hz Zone frequency',
        f'# TYPE zone_frequency_hz gauge',
        f'zone_frequency_hz{{zone="{zone}"}} {s["frequency_hz"]}',
        f'# HELP zone_voltage_v Zone average voltage',
        f'# TYPE zone_voltage_v gauge',
        f'zone_voltage_v{{zone="{zone}"}} {s["voltage_avg_v"]}',
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/shed-load", methods=["POST"])
def shed_load():
    data = request.get_json(force=True) or {}
    amount_mw = data.get("amount_mw", 50)
    with state_lock:
        for sname in list(state["sectors"].keys())[::-1]:  # shed from last sector first
            s = state["sectors"][sname]
            if s["load_mw"] > amount_mw:
                s["load_mw"] -= amount_mw
                s["status"] = "load_shed"
                state["current_load_mw"] = max(0, state["current_load_mw"] - amount_mw)
                break
    logger.info(f"[SHED-LOAD] Shed {amount_mw}MW in {ZONE_CFG.ZONE_NAME}")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Load shed {amount_mw}MW in {ZONE_CFG.ZONE_NAME}")
    return jsonify({"shed_mw": amount_mw, "zone": ZONE_CFG.ZONE_NAME})


@app.route("/feeder/<feeder_id>/isolate", methods=["POST"])
def isolate_feeder(feeder_id):
    with state_lock:
        if feeder_id in state["feeder_status"]:
            state["feeder_status"][feeder_id] = "isolated"
            # Reduce load
            state["current_load_mw"] = state["current_load_mw"] * 0.7
    logger.info(f"[ISOLATE] {feeder_id} isolated in {ZONE_CFG.ZONE_NAME}")
    return jsonify({"isolated": True, "feeder": feeder_id})


@app.route("/feeder/backup/activate", methods=["POST"])
def activate_backup_feeder():
    with state_lock:
        for fid, fstatus in state["feeder_status"].items():
            if fstatus == "isolated":
                state["feeder_status"][fid] = "backup"
    return jsonify({"backup_activated": True})


@app.route("/feeder/restore", methods=["POST"])
def restore_feeders():
    data = request.get_json(force=True) or {}
    feeders_to_restore = data.get("feeders", list(state["feeder_status"].keys()))
    with state_lock:
        for fid in feeders_to_restore:
            if fid in state["feeder_status"]:
                state["feeder_status"][fid] = "healthy"
        if state["substation_status"] == "tripped":
            state["substation_status"] = "healthy"
            state["current_load_mw"] = state["peak_load_mw"] * random.uniform(0.55, 0.70)
    logger.info(f"[RESTORE] Feeders restored in {ZONE_CFG.ZONE_NAME}: {feeders_to_restore}")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Feeders restored in {ZONE_CFG.ZONE_NAME}")
    return jsonify({"restored": True, "feeders": feeders_to_restore})


@app.route("/capacitor-bank/activate", methods=["POST"])
def activate_capacitor():
    with state_lock:
        state["capacitor_bank_active"] = True
        state["reactive_power_kvar"] = state["reactive_power_kvar"] * 0.6
        state["voltage_avg_v"] = round(state["voltage_avg_v"] + 3, 2)
    logger.info(f"[CAPACITOR] Bank activated in {ZONE_CFG.ZONE_NAME}")
    return jsonify({"capacitor_bank_active": True})


@app.route("/inductive-loads/shed", methods=["POST"])
def shed_inductive():
    data = request.get_json(force=True) or {}
    target_kvar = data.get("target_kvar_reduction", 200)
    with state_lock:
        state["reactive_power_kvar"] = max(50,
            state["reactive_power_kvar"] - target_kvar * random.uniform(0.8, 1.0))
        state["power_factor"] = min(0.98, state["power_factor"] + 0.05)
    return jsonify({"shed_kvar": target_kvar})


@app.route("/feeder/<feeder_id>/de-energize", methods=["POST"])
def de_energize_feeder(feeder_id):
    with state_lock:
        if feeder_id in state["feeder_status"]:
            state["feeder_status"][feeder_id] = "de-energized"
    return jsonify({"de-energized": True, "feeder": feeder_id})


@app.route("/tap-change", methods=["POST"])
def tap_change():
    data = request.get_json(force=True) or {}
    new_pos = data.get("position", 0)
    with state_lock:
        # Each tap step = 1.5V boost
        state["tap_v_offset"] = new_pos * 1.5
    return jsonify({"tap_v_offset": state["tap_v_offset"]})




@app.route("/demo/inject", methods=["POST"])
def demo_inject():
    data = request.get_json(force=True) or {}
    fault_type = data.get("type", "feeder_overload")
    with state_lock:
        if fault_type == "feeder_overload":
            sector = data.get("sector", "sector-1")
            magnitude_pct = data.get("magnitude_percent", 150)
            if sector in state["sectors"]:
                cap = state["sectors"][sector]["feeder_capacity_mw"]
                state["sectors"][sector]["load_mw"] = cap * magnitude_pct / 100
                state["sectors"][sector]["status"] = "overloaded"
                state["sectors"][sector]["voltage_v"] = random.uniform(195, 210)
                state["current_load_mw"] += cap * (magnitude_pct - 100) / 100
                state["load_percent"] = round(
                    state["current_load_mw"] / state["peak_load_mw"] * 100, 1)
            state["active_events"] += 1

        elif fault_type == "frequency_deviation":
            state["frequency_hz"] = random.uniform(49.2, 49.6)

        elif fault_type == "current_surge":
            # Simulate a current spike causing load surge
            amps = data.get("amps_a", random.uniform(450, 600))
            surge_mw = amps * 0.4  # approximate MW from current spike
            state["current_load_mw"] = min(
                state["peak_load_mw"] * 1.15, state["current_load_mw"] + surge_mw)
            state["load_percent"] = round(
                state["current_load_mw"] / state["peak_load_mw"] * 100, 1)
            state["voltage_avg_v"] = random.uniform(205, 218)
            state["frequency_hz"] = round(max(49.0, state["frequency_hz"] - 0.4), 3)
            state["active_events"] += 1

    logger.warning(f"[INJECT] {fault_type} in {ZONE_CFG.ZONE_NAME}")
    write_simulation_log(SERVICE_NAME, "INJECT",
                         f"{fault_type} in {ZONE_CFG.ZONE_NAME}")
    return jsonify({"injected": True, "fault_type": fault_type,
                    "component": f"zone-{ZONE_CFG.ZONE_NAME}"})


@app.route("/demo/reset")
def demo_reset():
    with state_lock:
        state["substation_status"] = "healthy"
        state["relay_status"] = "armed"
        state["capacitor_bank_active"] = False
        state["frequency_hz"] = 50.0
        state["voltage_avg_v"] = random.uniform(228, 231)
        state["current_load_mw"] = state["peak_load_mw"] * random.uniform(0.55, 0.72)
        state["load_percent"] = round(
            state["current_load_mw"] / state["peak_load_mw"] * 100, 1)
        state["active_events"] = 0
        for fid in state["feeder_status"]:
            state["feeder_status"][fid] = "healthy"
        for s in state["sectors"].values():
            s["status"] = "normal"
    return jsonify({"reset": True})


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {PORT} (zone={ZONE_CFG.ZONE_NAME})")
    threading.Thread(target=simulate, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
