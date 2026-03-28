"""
services/fault-detection/app.py
================================
Real-time electrical fault detection service.
Hosts THE ML model. Generates synthetic waveform-derived metrics.

DETECTS:
  1. Earth Fault
  2. Short Circuit
  3. Arc Fault
  4. Insulation Breakdown
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
SERVICE_NAME = "fault-detection"
PORT = 5010
START_TIME = time.time()
logger = setup_logger(SERVICE_NAME)

ZONE_NAMES = ["north", "south", "east", "west", "central"]
NUM_FEEDERS_PER_ZONE = 3
TOTAL_FEEDERS = len(ZONE_NAMES) * NUM_FEEDERS_PER_ZONE

state_lock = threading.Lock()


def _init_feeders():
    feeders = []
    for zone in ZONE_NAMES:
        for fi in range(1, NUM_FEEDERS_PER_ZONE + 1):
            phase_a = random.uniform(180, 220)
            feeders.append({
                "feeder_id":               f"{zone}-feeder-{fi}",
                "zone":                    zone,
                "phase_a_current_a":       phase_a,
                "phase_b_current_a":       phase_a * random.uniform(0.97, 1.03),
                "phase_c_current_a":       phase_a * random.uniform(0.97, 1.03),
                "residual_current_ma":     random.uniform(0, 50),
                "current_thd_percent":     random.uniform(2, 8),
                "insulation_resistance_mohm": random.uniform(85, 100),
                "arc_signature_score":     random.uniform(0, 0.12),
                "fault_probability":       random.uniform(0, 0.10),
                "status":                  "normal",
                "fault_type":              None,
            })
    return feeders


state = {
    "feeders": _init_feeders(),
    "arc_signature_score_max": 0.05,
    "fault_probability_max":   0.06,
    "active_faults": [],
    "active_faults_count": 0,
    "total_faults_detected": 0,
    "phase_a_current_avg": 200.0,
    "phase_b_current_avg": 200.0,
    "phase_c_current_avg": 200.0,
    "residual_current_ma_max": 20.0,
    "current_thd_percent_avg": 4.5,
    "insulation_resistance_min_mohm": 90.0,
}


def simulate_waveforms():
    """Continuously update electrical waveform metrics for all feeders."""
    t = 0
    while True:
        with state_lock:
            max_arc = 0
            max_fault_prob = 0
            max_residual = 0
            all_thd = []
            all_insulation = []
            all_pa = []

            for f in state["feeders"]:
                if f["status"] in ("isolated", "de-energized"):
                    continue

                # Natural current fluctuation with sine wave
                base_current = 200 + 30 * math.sin(t * 0.1 + hash(f["feeder_id"]) % 10)
                noise = random.gauss(0, 2)
                f["phase_a_current_a"] = round(max(0, base_current + noise), 1)
                f["phase_b_current_a"] = round(
                    max(0, base_current * random.uniform(0.97, 1.03) + noise), 1)
                f["phase_c_current_a"] = round(
                    max(0, base_current * random.uniform(0.97, 1.03) + noise), 1)
                all_pa.append(f["phase_a_current_a"])

                # Residual current (normal <50 mA)
                f["residual_current_ma"] = round(
                    max(0, f["residual_current_ma"] + random.gauss(0, 1)), 2)
                max_residual = max(max_residual, f["residual_current_ma"])

                # THD (normal 2-8%)
                f["current_thd_percent"] = round(
                    max(1, min(50, f["current_thd_percent"] + random.gauss(0, 0.1))), 2)
                all_thd.append(f["current_thd_percent"])

                # Insulation slowly recovers if normal
                if f["status"] == "normal":
                    f["insulation_resistance_mohm"] = min(100,
                        f["insulation_resistance_mohm"] + random.uniform(0, 0.005))
                all_insulation.append(f["insulation_resistance_mohm"])

                # Arc signature (normal <0.15)
                f["arc_signature_score"] = round(
                    max(0, min(1, f["arc_signature_score"] + random.gauss(0, 0.002))), 3)
                max_arc = max(max_arc, f["arc_signature_score"])

                # Fault probability (composite ML-like score)
                fp = (
                    (f["residual_current_ma"] / 2000) * 0.4 +
                    f["arc_signature_score"] * 0.3 +
                    ((100 - f["insulation_resistance_mohm"]) / 100) * 0.15 +
                    (f["current_thd_percent"] / 55) * 0.15
                )
                f["fault_probability"] = round(min(1, max(0, fp)), 3)
                max_fault_prob = max(max_fault_prob, f["fault_probability"])

            state["arc_signature_score_max"] = round(max_arc, 3)
            state["fault_probability_max"]   = round(max_fault_prob, 3)
            state["residual_current_ma_max"]  = round(max_residual, 2)
            state["current_thd_percent_avg"]  = round(
                sum(all_thd) / len(all_thd) if all_thd else 4, 2)
            state["insulation_resistance_min_mohm"] = round(
                min(all_insulation) if all_insulation else 90, 2)
            state["phase_a_current_avg"] = round(
                sum(all_pa) / len(all_pa) if all_pa else 200, 1)

            # Update active faults
            active = [
                {"feeder_id": f["feeder_id"], "fault_type": f["fault_type"],
                 "probability": f["fault_probability"]}
                for f in state["feeders"]
                if f["status"] not in ("normal", "isolated", "de-energized")
                and f["fault_type"] is not None
            ]
            state["active_faults"] = active
            state["active_faults_count"] = len(active)

        t += 1
        time.sleep(3)


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
        '# HELP fd_fault_probability_max Maximum fault probability detected',
        '# TYPE fd_fault_probability_max gauge',
        f'fd_fault_probability_max {s["fault_probability_max"]}',
        '# HELP fd_arc_signature_score_max Maximum arc signature score',
        '# TYPE fd_arc_signature_score_max gauge',
        f'fd_arc_signature_score_max {s["arc_signature_score_max"]}',
        '# HELP fd_active_faults_count Number of active faults',
        '# TYPE fd_active_faults_count gauge',
        f'fd_active_faults_count {s["active_faults_count"]}',
        '# HELP fd_residual_current_ma_max Maximum residual current in mA',
        '# TYPE fd_residual_current_ma_max gauge',
        f'fd_residual_current_ma_max {s["residual_current_ma_max"]}',
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/feeder/<feeder_id>/flag-maintenance", methods=["POST"])
def flag_maintenance(feeder_id):
    with state_lock:
        for f in state["feeders"]:
            if f["feeder_id"] == feeder_id:
                f["status"] = "maintenance-flagged"
    return jsonify({"flagged": True, "feeder": feeder_id})


@app.route("/demo/inject", methods=["POST"])
def demo_inject():
    data = request.get_json(force=True) or {}
    fault_type = data.get("type", "earth_fault")
    zone = data.get("zone", "central")
    feeder = data.get("feeder", "feeder-1")
    feeder_id = f"{zone}-{feeder}"

    with state_lock:
        target = None
        for f in state["feeders"]:
            if f["feeder_id"] == feeder_id:
                target = f
                break
        if target is None and state["feeders"]:
            target = state["feeders"][random.randint(0, len(state["feeders"]) - 1)]

        if target:
            target["fault_type"] = fault_type
            if fault_type == "earth_fault":
                target["residual_current_ma"] = data.get("residual_current_ma",
                    random.uniform(500, 1800))
                target["current_thd_percent"] = random.uniform(18, 45)
                target["status"] = "earth_fault"
                state["residual_current_ma_max"] = target["residual_current_ma"]

            elif fault_type == "short_circuit":
                target["phase_a_current_a"] *= random.uniform(5, 10)
                target["status"] = "short_circuit"

            elif fault_type == "arc_fault":
                target["arc_signature_score"] = data.get("arc_score",
                    random.uniform(0.75, 0.98))
                target["current_thd_percent"] = random.uniform(22, 55)
                target["insulation_resistance_mohm"] = random.uniform(0.1, 2.0)
                target["status"] = "arc_fault"
                state["arc_signature_score_max"] = target["arc_signature_score"]

            elif fault_type == "insulation_breakdown":
                target["insulation_resistance_mohm"] = random.uniform(1, 10)
                target["status"] = "insulation_breakdown"

            state["total_faults_detected"] += 1

    logger.warning(f"[INJECT] {fault_type} on feeder {feeder_id}")
    write_simulation_log(SERVICE_NAME, "INJECT",
                         f"{fault_type} on feeder {feeder_id}")
    return jsonify({"injected": True, "fault_type": fault_type, "component": feeder_id})


@app.route("/demo/reset")
def demo_reset():
    with state_lock:
        for f in state["feeders"]:
            f["status"] = "normal"
            f["fault_type"] = None
            f["residual_current_ma"] = random.uniform(0, 50)
            f["arc_signature_score"] = random.uniform(0, 0.12)
            f["insulation_resistance_mohm"] = random.uniform(85, 100)
        state["active_faults"] = []
        state["active_faults_count"] = 0
        state["arc_signature_score_max"] = 0.05
        state["fault_probability_max"] = 0.06
        state["residual_current_ma_max"] = 20.0
    return jsonify({"reset": True})


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {PORT}")
    threading.Thread(target=simulate_waveforms, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
