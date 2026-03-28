"""
services/grid-controller/app.py
================================
SCADA (Supervisory Control and Data Acquisition) hub.
Central nervous system of the Smart Grid.

Responsibilities:
- Aggregates metrics from all other services
- Maintains alert log and remediation log
- Routes ML remediation commands to target services
- Exposes /metrics in Prometheus format
- Exposes /alerts and /remediation-log for frontend
"""

import os
import sys
import time
import threading
import logging
import json
import datetime
import random
import subprocess
from collections import deque
from flask import Flask, request, jsonify, Response
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services.shared.logger import setup_logger, write_simulation_log

app = Flask(__name__)

# ─── Config ────────────────────────────────────────────────────────────────────
SERVICE_NAME = "grid-controller"
PORT = 5001
START_TIME = time.time()

ZONE_PORTS = {
    "north": 5003, "south": 5004, "east": 5005,
    "west": 5006, "central": 5007,
}
# Now counting 5 functional nodes instead of individual services
ALL_SERVICE_PORTS = [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010]

# ─── Shared state ──────────────────────────────────────────────────────────────
state_lock = threading.Lock()
state = {
    "system_status": 0,          # 0=healthy 1=degraded 2=critical
    "grid_total_load_mw": 3200.0,
    "grid_capacity_mw": 5240.0,
    "grid_load_percent": 61.1,
    "active_alerts_count": 0,
    "services_online_count": 5,
    "last_poll_latency_ms": 0,
    "remediation_actions_count": 0,
    "alert_rate_per_minute": 0.0,
    "remediation_count_session": 0,
    "is_simulating": True,
    "simulation_start_time": time.time(),
}

alerts = deque(maxlen=200)   # live alert feed
remediation_log = deque(maxlen=100)
alert_timestamps = deque(maxlen=300)  # for rate calculation

# ─── Background data cache (avoids live HTTP in /metrics/summary) ─────────────
service_cache = {
    "transformer_summary": {"avg_temp": 65.0, "max_load": 75.0},
    "lb_data": {},
    "vr_data": {},
}

# ─── Logger ────────────────────────────────────────────────────────────────────
logger = setup_logger(SERVICE_NAME)

# ─── Background polling ─────────────────────────────────────────────────────────

def poll_services():
    """Poll all services every 5s to aggregate top-level grid metrics."""
    global state
    while True:
        try:
            t_start = time.time()
            online = 0
            total_load = 0.0
            capacity = 5240.0

            # ── Node 1: Infrastructure (Transformer 5002) ──────────────────
            node1 = 0
            try:
                r = requests.get("http://localhost:5002/status", timeout=2)
                if r.status_code == 200:
                    data = r.json()
                    ts = data.get("transformers", [])
                    restarting = any(t.get("_is_restarting") for t in ts)
                    if not restarting:
                        node1 = 1
            except: pass

            # ── Node 2: Distribution (Zones 5003-5007) ──────────────────
            node2 = 1
            for zp in [5003, 5004, 5005, 5006, 5007]:
                try:
                    r = requests.get(f"http://localhost:{zp}/health", timeout=1)
                    if r.status_code != 200:
                        node2 = 0
                        break
                except:
                    node2 = 0
                    break

            # ── Node 3-5: Optimization, Stability, Security ─────────────
            node3 = node4 = node5 = 0
            try:
                if requests.get("http://localhost:5008/health", timeout=1).status_code == 200: node3 = 1
            except: pass
            try:
                if requests.get("http://localhost:5009/health", timeout=1).status_code == 200: node4 = 1
            except: pass
            try:
                if requests.get("http://localhost:5010/health", timeout=1).status_code == 200: node5 = 1
            except: pass

            online = node1 + node2 + node3 + node4 + node5

            # Aggregate zone loads
            zone_loads = []
            for zone, port in ZONE_PORTS.items():
                try:
                    r = requests.get(f"http://localhost:{port}/status", timeout=2)
                    if r.status_code == 200:
                        data = r.json()
                        zone_loads.append(data.get("current_load_mw", 0))
                except Exception:
                    pass

            if zone_loads:
                total_load = sum(zone_loads)

            # ── Cache transformer / LB / VR data ──────────────────────────────
            try:
                r = requests.get("http://localhost:5002/status", timeout=2)
                if r.status_code == 200:
                    ts = r.json().get("transformers", [])
                    if ts:
                        service_cache["transformer_summary"] = {
                            "avg_temp": round(sum(t.get("temperature_c", 60) for t in ts) / len(ts), 1),
                            "max_load": round(max(t.get("load_percent", 0) for t in ts), 1),
                        }
            except: pass

            try:
                r = requests.get("http://localhost:5008/status", timeout=1)
                if r.status_code == 200:
                    service_cache["lb_data"] = r.json()
            except: pass

            try:
                r = requests.get("http://localhost:5009/status", timeout=1)
                if r.status_code == 200:
                    service_cache["vr_data"] = r.json()
            except: pass

            latency_ms = (time.time() - t_start) * 1000

            # Calculate alert rate
            now = time.time()
            minute_ago = now - 60
            recent_alerts = [t for t in alert_timestamps if t > minute_ago]
            alert_rate = len(recent_alerts) / 1.0

            # Determine system status
            load_pct = total_load / capacity * 100 if capacity > 0 else 0
            sys_status = 0
            if load_pct > 90 or state["active_alerts_count"] > 5:
                sys_status = 2
            elif load_pct > 80 or state["active_alerts_count"] > 2:
                sys_status = 1

            with state_lock:
                state["grid_total_load_mw"] = round(total_load, 1)
                state["grid_load_percent"]   = round(load_pct, 1)
                state["services_online_count"] = online
                state["last_poll_latency_ms"]  = round(latency_ms, 1)
                state["system_status"]          = sys_status
                state["alert_rate_per_minute"]  = round(alert_rate, 2)

            # logger.info(f"[POLL] Load={total_load:.0f}MW Online={online}/5 Latency={latency_ms:.0f}ms")

        except Exception as e:
            logger.error(f"[POLL-ERROR] {e}")

        time.sleep(5)


def simulate_natural_variation():
    """Add small natural fluctuations to grid metrics."""
    while True:
        with state_lock:
            # Only vary if simulation is active
            if state.get("is_simulating"):
                base = state["grid_total_load_mw"]
                delta = random.gauss(0, 15)
                new_load = max(2500, min(5000, base + delta))
                state["grid_total_load_mw"] = round(new_load, 1)
                state["grid_load_percent"] = round(new_load / state["grid_capacity_mw"] * 100, 1)
        time.sleep(3)


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "service": SERVICE_NAME,
        "uptime_s": round(time.time() - START_TIME, 1),
    })


@app.route("/status")
def status():
    with state_lock:
        return jsonify(dict(state))


@app.route("/metrics")
def metrics():
    with state_lock:
        s = dict(state)
    lines = [
        f'grid_total_load_mw {s["grid_total_load_mw"]}',
        f'grid_capacity_mw {s["grid_capacity_mw"]}',
        f'grid_load_percent {s["grid_load_percent"]}',
        f'active_alerts_count {s["active_alerts_count"]}',
        f'services_online_count {s["services_online_count"]}',
        f'system_status {s["system_status"]}',
        f'remediation_actions_count {s["remediation_actions_count"]}',
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/metrics/summary")
def metrics_summary():
    """Aggregated summary for the React frontend. Uses cached data — no live HTTP calls."""
    with state_lock:
        s = dict(state)

    transformer_summary = service_cache["transformer_summary"]
    lb_data             = service_cache["lb_data"]
    vr_data             = service_cache["vr_data"]

    risk = "LOW"
    if s["grid_load_percent"] > 85: risk = "CRITICAL"
    elif s["grid_load_percent"] > 75: risk = "HIGH"
    elif s["grid_load_percent"] > 65: risk = "MEDIUM"

    uptime_s = 0
    if s.get("is_simulating") and s.get("simulation_start_time"):
        uptime_s = int(time.time() - s["simulation_start_time"])

    status_text = ["HEALTHY", "DEGRADED", "CRITICAL"][s["system_status"]]

    return jsonify({
        **s,
        "avg_transformer_temp": transformer_summary["avg_temp"],
        "max_transformer_load": transformer_summary["max_load"],
        "overload_risk": risk,
        "status_text": status_text,
        "simulation_uptime_s": uptime_s,
        "load_balancer": lb_data,
        "voltage_regulator": vr_data,
    })


@app.route("/alert", methods=["POST"])
def receive_alert():
    data = request.get_json(force=True) or {}
    now = datetime.datetime.now()
    alert = {
        "id": f"a-{int(time.time()*1000)}",
        "timestamp": now.isoformat(),
        "timestamp_display": now.strftime("%H:%M:%S"),
        "severity": data.get("severity", "warning").upper(),
        "service": data.get("service", "unknown"),
        "component": data.get("component", ""),
        "zone": data.get("zone", ""),
        "message": data.get("message", ""),
        "fault_type": data.get("fault_type", ""),
    }
    alerts.appendleft(alert)
    alert_timestamps.append(time.time())

    with state_lock:
        state["active_alerts_count"] = len([
            a for a in alerts
            if (time.time() - datetime.datetime.fromisoformat(a["timestamp"]).timestamp()) < 300
        ])

    logger.warning(f"[ALERT] {alert['severity']} | {alert['service']} | {alert['message']}")
    write_simulation_log(SERVICE_NAME, "ALERT", f"{alert['severity']} from {alert['service']}: {alert['message']}")
    return jsonify({"received": True, "alert_id": alert["id"]})


@app.route("/alerts")
def get_alerts():
    limit = int(request.args.get("limit", 50))
    return jsonify(list(alerts)[:limit])


@app.route("/remediation-log", methods=["GET"])
def get_remediation_log():
    limit = int(request.args.get("limit", 30))
    return jsonify(list(remediation_log)[:limit])


@app.route("/remediation-log", methods=["POST"])
def post_remediation_log():
    data = request.get_json(force=True) or {}
    now = datetime.datetime.now()
    
    rid = data.get("remediation_id") or data.get("id")
    existing_entry = None
    if rid:
        with state_lock:
            for entry in remediation_log:
                if entry.get("remediation_id") == rid or entry.get("id") == rid:
                    existing_entry = entry
                    break
    
    if existing_entry:
        with state_lock:
            existing_entry.update(data)
            existing_entry["last_update"] = now.isoformat()
        return jsonify({"updated": True, "id": rid})
    else:
        entry = {
            "id": f"r-{int(time.time()*1000)}",
            "timestamp": now.isoformat(),
            "timestamp_display": now.strftime("%H:%M:%S"),
            "remediation_id": rid,
            **data,
        }
        remediation_log.appendleft(entry)
        with state_lock:
            state["remediation_actions_count"] += 1
            state["remediation_count_session"] += 1
        
        write_simulation_log(SERVICE_NAME, "REMEDIATE", f"[{data.get('fault_type','?')}] {data.get('status','?')}")
        return jsonify({"created": True, "id": entry["id"]})


@app.route("/simulation/start", methods=["POST"])
def start_simulation():
    """Toggle simulation to active. Master runner (run_app.py) polls this state."""
    with state_lock:
        state["is_simulating"] = True
        state["simulation_start_time"] = time.time()
        state["remediation_count_session"] = 0
        
    logger.info("[SIMULATION] Activated via Dashboard.")
    write_simulation_log(SERVICE_NAME, "SIMULATE", "Simulation STARTED via dashboard")
    return jsonify({"status": "started", "timestamp": state["simulation_start_time"]})


@app.route("/simulation/stop", methods=["POST"])
def stop_simulation():
    """Deactivate simulation and reset all grid components to a healthy state."""
    logger.info("[SIMULATION] Deactivating simulation and resetting grid...")
    
    # Reset all components
    for port in [5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010]:
        try:
            requests.get(f"http://localhost:{port}/demo/reset", timeout=1)
        except Exception:
            pass
            
    with state_lock:
        state["is_simulating"] = False
        state["simulation_start_time"] = None
        state["system_status"] = 0
        state["active_alerts_count"] = 0
        remediation_log.clear()
        alerts.clear()

    write_simulation_log(SERVICE_NAME, "SIMULATE", "Simulation STOPPED and RESET via dashboard")
    return jsonify({"status": "stopped_and_reset"})


@app.route("/demo/inject", methods=["POST"])
def demo_inject():
    data = request.get_json(force=True) or {}
    fault_type = data.get("type", "communication_blackout")
    if fault_type == "communication_blackout":
        with state_lock:
            state["system_status"] = 2
            state["last_poll_latency_ms"] = random.uniform(2000, 5000)
    logger.warning(f"[INJECT] {fault_type} injected into grid-controller")
    return jsonify({"injected": True, "fault_type": fault_type})


@app.route("/demo/reset")
def demo_reset():
    with state_lock:
        state["system_status"] = 0
        state["active_alerts_count"] = 0
    return jsonify({"reset": True})


if __name__ == "__main__":
    # ── Fresh start: clear all in-memory state ─────────────────────────────
    alerts.clear()
    remediation_log.clear()
    alert_timestamps.clear()
    with state_lock:
        state["active_alerts_count"]       = 0
        state["remediation_actions_count"] = 0
        state["remediation_count_session"] = 0

    # Clear simulation log file on start
    sim_log_path = os.path.join(ROOT, "testing", "logs", "simulation_run.txt")
    try:
        if os.path.exists(sim_log_path):
            with open(sim_log_path, "w") as f:
                f.truncate(0)
    except Exception:
        pass

    logger.info(f"Starting {SERVICE_NAME} on port {PORT} — fresh state, 0 logs")
    threading.Thread(target=poll_services, daemon=True).start()
    threading.Thread(target=simulate_natural_variation, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
