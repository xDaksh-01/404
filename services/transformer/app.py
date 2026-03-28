"""
services/transformer/app.py
============================
Manages 16 physical transformers across 5 zones.
Each transformer is a stateful object.

CAN BREAK:
  1. Thermal Overload
  2. Voltage Instability
  3. Oil Degradation
  4. Cooling Fan Failure
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

app = Flask(__name__)
SERVICE_NAME = "transformer"
PORT = 5002
START_TIME = time.time()
logger = setup_logger(SERVICE_NAME)
GRID_CONTROLLER_HOST = os.getenv("GRID_CONTROLLER_HOST", "localhost")

# ─── Transformer definitions ────────────────────────────────────────────────────
TRANSFORMER_SPECS = [
    {"id": "T1",  "zone": "north",   "capacity_mw": 280.0},
    {"id": "T2",  "zone": "north",   "capacity_mw": 295.0},
    {"id": "T3",  "zone": "north",   "capacity_mw": 310.0},
    {"id": "T4",  "zone": "south",   "capacity_mw": 265.0},
    {"id": "T5",  "zone": "south",   "capacity_mw": 290.0},
    {"id": "T6",  "zone": "east",    "capacity_mw": 275.0},
    {"id": "T7",  "zone": "east",    "capacity_mw": 285.0},
    {"id": "T8",  "zone": "east",    "capacity_mw": 300.0},
    {"id": "T9",  "zone": "east",    "capacity_mw": 270.0},
    {"id": "T10", "zone": "west",    "capacity_mw": 260.0},
    {"id": "T11", "zone": "west",    "capacity_mw": 285.0},
    {"id": "T12", "zone": "central", "capacity_mw": 290.0},
    {"id": "T13", "zone": "central", "capacity_mw": 305.0},
    {"id": "T14", "zone": "central", "capacity_mw": 295.0},
    {"id": "T15", "zone": "central", "capacity_mw": 310.0},
    {"id": "T16", "zone": "central", "capacity_mw": 285.0},
]

state_lock = threading.Lock()


def _make_transformer(spec):
    load_pct = random.uniform(45, 75)
    return {
        **spec,
        "status": "healthy",
        "load_mw": spec["capacity_mw"] * load_pct / 100,
        "load_percent": load_pct,
        "temperature_c": 50 + (load_pct / 100) ** 1.8 * 50,
        "voltage_output_v": 230 - (load_pct / 100) ** 1.5 * 20  + random.gauss(0, 0.5),
        "efficiency_percent": random.uniform(91, 96),
        "oil_level_percent": random.uniform(93, 99),
        "oil_temperature_c": 60 + load_pct * 0.3,
        "cooling_fan_status": "active",
        "cooling_active": False,
        "tap_position": 0,
        "winding_resistance_ohm": round(0.038 + random.uniform(0, 0.008), 4),
        "dissolved_gas_level": random.uniform(5, 25),
        "power_factor": random.uniform(0.91, 0.97),
        "uptime_hours": random.uniform(200, 8760),
        "fault_history": [],
        "load_limit_percent": 100,  # max allowed load (reduced during faults)
    }


transformers = {spec["id"]: _make_transformer(spec) for spec in TRANSFORMER_SPECS}


# ─── Background simulation ──────────────────────────────────────────────────────

def simulate():
    while True:
        with state_lock:
            for tid, t in transformers.items():
                # Natural drift
                load_drift = random.gauss(0, 1.5)
                new_load_pct = max(0, min(t["load_limit_percent"],
                                         t["load_percent"] + load_drift))
                t["load_percent"] = round(new_load_pct, 2)
                t["load_mw"] = round(t["capacity_mw"] * new_load_pct / 100, 1)

                # Temperature physics: rises with load, falls with cooling
                target_temp = 45 + (new_load_pct / 100) ** 1.8 * 55
                if t["cooling_active"]:
                    target_temp -= 12  # cooling effect
                if t["cooling_fan_status"] == "failed":
                    target_temp += 8  # lost cooling
                temp_drift = (target_temp - t["temperature_c"]) * 0.1 + random.gauss(0, 0.3)
                t["temperature_c"] = round(t["temperature_c"] + temp_drift, 2)

                # Voltage: droops with load
                nominal = 230
                t["voltage_output_v"] = round(
                    nominal - (new_load_pct / 100) ** 1.5 * 20
                    + random.gauss(0, 0.3) + t["tap_position"] * 1.5, 2)

                # Oil slowly degrades
                t["oil_level_percent"] = max(0,
                    t["oil_level_percent"] - random.uniform(0, 0.001))
                t["oil_temperature_c"] = round(t["temperature_c"] * 0.85
                    + random.gauss(0, 0.2), 2)
                t["dissolved_gas_level"] = round(max(0,
                    t["dissolved_gas_level"] + random.gauss(0, 0.05)), 2)

                # Power factor
                t["power_factor"] = round(max(0.7, min(0.99,
                    t["power_factor"] + random.gauss(0, 0.002))), 3)

                # Efficiency
                t["efficiency_percent"] = round(max(70, min(99,
                    96 - (new_load_pct / 100) ** 2 * 6 + random.gauss(0, 0.1))), 2)

                # Status update
                t["uptime_hours"] = round(t["uptime_hours"] + 5/3600, 3)

                if t["temperature_c"] > 90 or new_load_pct > 95:
                    t["status"] = "critical"
                elif t["temperature_c"] > 80 or new_load_pct > 85:
                    t["status"] = "warning"
                elif t["cooling_fan_status"] == "failed":
                    t["status"] = "warning"
                else:
                    t["status"] = "healthy"

                # Alert if critical
                if t["status"] == "critical":
                    try:
                        requests.post(f"http://{GRID_CONTROLLER_HOST}:5001/alert", json={
                            "severity": "critical",
                            "service": SERVICE_NAME,
                            "component": tid,
                            "zone": t["zone"],
                            "message": f"Transformer {tid} in {t['zone']} is CRITICAL "
                                       f"(temp={t['temperature_c']:.1f}°C, "
                                       f"load={new_load_pct:.1f}%)",
                        }, timeout=1)
                    except Exception:
                        pass

        time.sleep(5)


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "online", "service": SERVICE_NAME,
                    "uptime_s": round(time.time() - START_TIME, 1)})


@app.route("/status")
def status():
    with state_lock:
        ts = [dict(t) for t in transformers.values()]
    # Remove mutable list from response for performance
    for t in ts:
        t.pop("fault_history", None)
    return jsonify({"transformers": ts, "count": len(ts)})


@app.route("/transformer/<tid>")
def get_transformer(tid):
    with state_lock:
        if tid not in transformers:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(transformers[tid]))


@app.route("/transformer/<tid>/cooling", methods=["POST"])
def set_cooling(tid):
    data = request.get_json(force=True) or {}
    with state_lock:
        if tid not in transformers:
            return jsonify({"error": "not found"}), 404
        t = transformers[tid]
        t["cooling_active"] = data.get("activate", True)
        fan_speed = data.get("fan_speed", "maximum")
        if fan_speed == "maximum":
            t["cooling_active"] = True
        logger.info(f"[COOLING] {tid}: cooling_active={t['cooling_active']}")
        write_simulation_log(SERVICE_NAME, "REMEDIATE",
                             f"{tid} cooling set to active={t['cooling_active']}")
    return jsonify({"cooling_active": t["cooling_active"], "fan_speed": fan_speed})


@app.route("/transformer/<tid>/load-limit", methods=["POST"])
def set_load_limit(tid):
    data = request.get_json(force=True) or {}
    with state_lock:
        if tid not in transformers:
            return jsonify({"error": "not found"}), 404
        t = transformers[tid]
        limit = data.get("max_load_percent", 60)
        t["load_limit_percent"] = limit
        if t["load_percent"] > limit:
            t["load_percent"] = limit * random.uniform(0.85, 0.95)
            t["load_mw"] = t["capacity_mw"] * t["load_percent"] / 100
        logger.info(f"[LOAD-LIMIT] {tid}: max_load_percent={limit}")
    return jsonify({"transformer": tid, "max_load_percent": limit})


@app.route("/emergency-reduce", methods=["POST"])
def emergency_reduce():
    data = request.get_json(force=True) or {}
    reduce_pct = data.get("reduce_by_percent", 15)
    target = data.get("transformer_id")
    with state_lock:
        targets = [target] if target and target in transformers else list(transformers.keys())
        for tid in targets:
            t = transformers[tid]
            t["load_percent"] = max(20, t["load_percent"] * (1 - reduce_pct / 100))
            t["load_mw"] = t["capacity_mw"] * t["load_percent"] / 100
    logger.info(f"[EMERGENCY-REDUCE] Reduced load by {reduce_pct}% on {len(targets)} transformers")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Emergency load reduction {reduce_pct}% on {len(targets)} transformers")
    return jsonify({"reduced": True, "targets": targets, "reduce_by_percent": reduce_pct})


@app.route("/distribute", methods=["POST"])
def distribute():
    data = request.get_json(force=True) or {}
    rebalance_type = data.get("rebalance_type", "standard")
    with state_lock:
        loads = [t["load_percent"] for t in transformers.values()]
        avg = sum(loads) / len(loads)
        for t in transformers.values():
            if t["load_percent"] > avg + 10:
                diff = t["load_percent"] - avg
                t["load_percent"] = round(avg + diff * 0.5, 2)
                t["load_mw"] = t["capacity_mw"] * t["load_percent"] / 100
    return jsonify({"rebalanced": True, "type": rebalance_type})


@app.route("/metrics")
def prom_metrics():
    with state_lock:
        ts = list(transformers.values())
    lines = ['# HELP transformer_load_percent Transformer load percentage',
             '# TYPE transformer_load_percent gauge']
    for t in ts:
        lines.append(
            f'transformer_load_percent{{id="{t["id"]}",zone="{t["zone"]}"}} {t["load_percent"]}')
    lines += ['# HELP transformer_temperature_c Transformer temperature',
              '# TYPE transformer_temperature_c gauge']
    for t in ts:
        lines.append(
            f'transformer_temperature_c{{id="{t["id"]}",zone="{t["zone"]}"}} {t["temperature_c"]}')
    return Response("\n".join(lines) + "\n", mimetype="text/plain")




@app.route("/demo/inject", methods=["POST"])
def demo_inject():
    data = request.get_json(force=True) or {}
    fault_type = data.get("type", "thermal_overload")
    tid = data.get("transformer_id", "T3")
    
    with state_lock:
        if tid not in transformers:
            tid = list(transformers.keys())[0]
        t = transformers[tid]
        
        if fault_type in ("thermal_overload", "transformer_overload"):
            t["load_percent"] = data.get("load_percent", random.uniform(92, 99))
            t["temperature_c"] = data.get("temperature_c", random.uniform(90, 97))
            t["load_mw"] = t["capacity_mw"] * t["load_percent"] / 100
            t["status"] = "critical"
            t["efficiency_percent"] = random.uniform(78, 85)
            t["voltage_output_v"] = random.uniform(210, 218)
            
        elif fault_type == "cooling_fan_failure":
            t["cooling_fan_status"] = "failed"
            t["status"] = "warning"
            
        elif fault_type in ("voltage_instability", "voltage_spike"):
            if fault_type == "voltage_spike":
                # High voltage surge on transformer output
                t["voltage_output_v"] = data.get("voltage_v", random.uniform(265, 285))
                t["status"] = "warning"
                t["power_factor"] = random.uniform(0.72, 0.82)
            else:
                t["voltage_output_v"] = random.uniform(200, 213)
                t["power_factor"] = random.uniform(0.72, 0.82)
            
        elif fault_type == "oil_degradation":
            t["oil_level_percent"] = random.uniform(75, 84)
            t["dissolved_gas_level"] = random.uniform(80, 150)
            t["status"] = "warning"

    logger.warning(f"[INJECT] {fault_type} on transformer {tid}")
    write_simulation_log(SERVICE_NAME, "INJECT",
                         f"{fault_type} injected on transformer {tid}")
    return jsonify({"injected": True, "fault_type": fault_type, "component": tid})


@app.route("/demo/reset")
def demo_reset():
    with state_lock:
        for tid, spec in zip(transformers.keys(), TRANSFORMER_SPECS):
            transformers[tid].update({
                "status": "healthy",
                "cooling_active": False,
                "cooling_fan_status": "active",
                "load_limit_percent": 100,
                "load_percent": random.uniform(45, 75),
                "temperature_c": random.uniform(55, 70),
                "voltage_output_v": random.uniform(226, 232),
                "efficiency_percent": random.uniform(91, 96),
            })
    return jsonify({"reset": True})


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {PORT}")
    threading.Thread(target=simulate, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
