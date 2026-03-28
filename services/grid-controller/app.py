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

SERVICE_PORTS = {
    "grid-controller": 5001,
    "transformer": 5002,
    "zone-north": 5003,
    "zone-south": 5004,
    "zone-east": 5005,
    "zone-west": 5006,
    "zone-central": 5007,
    "load-balancer": 5008,
    "voltage-regulator": 5009,
    "fault-detection": 5010,
}
SERVICE_HOSTS = {
    "grid-controller": os.getenv("GRID_CONTROLLER_HOST", "localhost"),
    "transformer": os.getenv("TRANSFORMER_HOST", "localhost"),
    "zone-north": os.getenv("ZONE_NORTH_HOST", "localhost"),
    "zone-south": os.getenv("ZONE_SOUTH_HOST", "localhost"),
    "zone-east": os.getenv("ZONE_EAST_HOST", "localhost"),
    "zone-west": os.getenv("ZONE_WEST_HOST", "localhost"),
    "zone-central": os.getenv("ZONE_CENTRAL_HOST", "localhost"),
    "load-balancer": os.getenv("LOAD_BALANCER_HOST", "localhost"),
    "voltage-regulator": os.getenv("VOLTAGE_REGULATOR_HOST", "localhost"),
    "fault-detection": os.getenv("FAULT_DETECTION_HOST", "localhost"),
}
PORT_TO_SERVICE = {port: name for name, port in SERVICE_PORTS.items()}
KNOWN_FAULT_TYPES = [
    "voltage_overload",
    "power_redistribution",
    "voltage_spike",
    "current_surge",
    "transformer_overload",
    "rebooting_overheat",
]


def _empty_fault_counts() -> dict:
    return {ft: 0 for ft in KNOWN_FAULT_TYPES}


def service_url(service_name: str, path: str) -> str:
    return f"http://{SERVICE_HOSTS[service_name]}:{SERVICE_PORTS[service_name]}{path}"


def service_url_by_port(port: int, path: str) -> str:
    service_name = PORT_TO_SERVICE[port]
    return service_url(service_name, path)

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
    "resolved_alerts_count": 0,
    "detected_faults_total": 0,
    "fault_type_counts": _empty_fault_counts(),
    "is_simulating": True,
    "simulation_start_time": time.time(),
}

alerts = deque(maxlen=200)   # live alert feed
remediation_log = deque(maxlen=100)
alert_timestamps = deque(maxlen=300)  # for rate calculation

ALERT_DEDUP_WINDOW_S = 45
ACTIVE_ALERT_TTL_S = 300

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
                r = requests.get(service_url("transformer", "/status"), timeout=2)
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
                    r = requests.get(service_url_by_port(zp, "/health"), timeout=1)
                    if r.status_code != 200:
                        node2 = 0
                        break
                except:
                    node2 = 0
                    break

            # ── Node 3-5: Optimization, Stability, Security ─────────────
            node3 = node4 = node5 = 0
            try:
                if requests.get(service_url("load-balancer", "/health"), timeout=1).status_code == 200: node3 = 1
            except: pass
            try:
                if requests.get(service_url("voltage-regulator", "/health"), timeout=1).status_code == 200: node4 = 1
            except: pass
            try:
                if requests.get(service_url("fault-detection", "/health"), timeout=1).status_code == 200: node5 = 1
            except: pass

            online = node1 + node2 + node3 + node4 + node5

            # Aggregate zone loads
            zone_loads = []
            for zone, port in ZONE_PORTS.items():
                try:
                    r = requests.get(service_url_by_port(port, "/status"), timeout=2)
                    if r.status_code == 200:
                        data = r.json()
                        zone_loads.append(data.get("current_load_mw", 0))
                except Exception:
                    pass

            if zone_loads:
                total_load = sum(zone_loads)

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


def _alert_fingerprint(alert: dict) -> str:
    return "|".join([
        alert.get("service", ""),
        alert.get("fault_type", ""),
        alert.get("zone", ""),
        alert.get("component", ""),
        alert.get("message", ""),
    ])


def _refresh_active_alerts_count_locked(now_ts: float | None = None):
    now_ts = now_ts or time.time()
    state["active_alerts_count"] = len([
        a for a in alerts
        if a.get("status", "OPEN") == "OPEN"
        and (now_ts - datetime.datetime.fromisoformat(a["timestamp"]).timestamp()) < ACTIVE_ALERT_TTL_S
    ])


def _resolve_related_alerts_locked(fault_type: str, zone: str = "", component: str = "") -> int:
    """Resolve open alerts that match the same incident footprint."""
    resolved_now = 0
    now = datetime.datetime.now().isoformat()
    for alert in alerts:
        if alert.get("status") != "OPEN":
            continue
        if fault_type and alert.get("fault_type") != fault_type:
            continue
        if zone and alert.get("zone") and alert.get("zone") != zone:
            continue
        if component and alert.get("component") and alert.get("component") != component:
            continue
        alert["status"] = "RESOLVED"
        alert["resolved_timestamp"] = now
        resolved_now += 1
    if resolved_now:
        state["resolved_alerts_count"] += resolved_now
    return resolved_now


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
        fault_counts = dict(s.get("fault_type_counts", {}))
    lines = [
        '# HELP grid_total_load_mw Total real power demand on the smart grid in MW',
        '# TYPE grid_total_load_mw gauge',
        f'grid_total_load_mw {s["grid_total_load_mw"]}',
        '# HELP grid_capacity_mw Total nominal capacity of the smart grid in MW',
        '# TYPE grid_capacity_mw gauge',
        f'grid_capacity_mw {s["grid_capacity_mw"]}',
        '# HELP grid_load_percent Grid loading as percentage of total capacity',
        '# TYPE grid_load_percent gauge',
        f'grid_load_percent {s["grid_load_percent"]}',
        '# HELP active_alerts_count Number of currently active alerts in SCADA',
        '# TYPE active_alerts_count gauge',
        f'active_alerts_count {s["active_alerts_count"]}',
        '# HELP services_online_count Number of online services observed by SCADA',
        '# TYPE services_online_count gauge',
        f'services_online_count {s["services_online_count"]}',
        '# HELP system_status Grid health state where 0=healthy 1=degraded 2=critical',
        '# TYPE system_status gauge',
        f'system_status {s["system_status"]}',
        '# HELP remediation_actions_count Total remediation actions executed',
        '# TYPE remediation_actions_count counter',
        f'remediation_actions_count {s["remediation_actions_count"]}',
        '# HELP resolved_alerts_count Total alerts marked as resolved by remediation',
        '# TYPE resolved_alerts_count counter',
        f'resolved_alerts_count {s["resolved_alerts_count"]}',
        '# HELP ml_detected_faults_total Total ML-detected fault alerts grouped by fault type',
        '# TYPE ml_detected_faults_total counter',
        f'ml_detected_faults_total {s["detected_faults_total"]}',
    ]
    for ft, count in sorted(fault_counts.items()):
        fault_label = str(ft).replace('"', "")
        lines.append(f'ml_detected_faults_total{{fault_type="{fault_label}"}} {count}')
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/metrics/summary")
def metrics_summary():
    """Aggregated summary for the React frontend."""
    with state_lock:
        s = dict(state)

    transformer_summary = {"avg_temp": 65.0, "max_load": 75.0}
    lb_data = {}
    vr_data = {}

    def fetch_service(name, url, timeout=1.5):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return name, r.json()
        except:
            pass
        return name, None

    # Poll sub-services in parallel to avoid timeout (Frontend has 3s limit)
    targets = [
        ("tr", service_url("transformer", "/status"), 1.5),
        ("lb", service_url("load-balancer", "/status"), 1.2),
        ("vr", service_url("voltage-regulator", "/status"), 1.2),
    ]

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = dict(executor.map(lambda t: fetch_service(*t), targets))

    # Process Transformer data
    tr_res = results.get("tr")
    if tr_res:
        ts = tr_res.get("transformers", [])
        if ts:
            transformer_summary["avg_temp"] = round(sum(t.get("temperature_c", 60) for t in ts) / len(ts), 1)
            transformer_summary["max_load"] = round(max(t.get("load_percent", 0) for t in ts), 1)

    lb_data = results.get("lb") or {}
    vr_data = results.get("vr") or {}

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
    now_ts = time.time()
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
        "status": "OPEN",
        "resolved_timestamp": None,
        "occurrences": 1,
        "last_seen": now.isoformat(),
    }
    alert["fingerprint"] = _alert_fingerprint(alert)

    deduped_alert_id = None
    with state_lock:
        for existing in alerts:
            if existing.get("fingerprint") != alert["fingerprint"]:
                continue
            if existing.get("status", "OPEN") != "OPEN":
                continue

            prev_ts = datetime.datetime.fromisoformat(existing["timestamp"]).timestamp()
            if now_ts - prev_ts <= ALERT_DEDUP_WINDOW_S:
                existing["occurrences"] = existing.get("occurrences", 1) + 1
                existing["last_seen"] = alert["last_seen"]
                existing["timestamp_display"] = alert["timestamp_display"]
                deduped_alert_id = existing["id"]
                break

        if deduped_alert_id is None:
            alerts.appendleft(alert)
            alert_timestamps.append(now_ts)

            if alert["service"] == "ml-anomaly-detector" and alert.get("fault_type"):
                ft = alert["fault_type"]
                state["detected_faults_total"] += 1
                counts = state.setdefault("fault_type_counts", {})
                counts[ft] = counts.get(ft, 0) + 1

        _refresh_active_alerts_count_locked(now_ts)

    if deduped_alert_id is None:
        logger.warning(f"[ALERT] {alert['severity']} | {alert['service']} | {alert['message']}")
        write_simulation_log(SERVICE_NAME, "ALERT", f"{alert['severity']} from {alert['service']}: {alert['message']}")
        return jsonify({"received": True, "alert_id": alert["id"], "deduplicated": False})

    logger.info(f"[ALERT-DEDUPE] {alert['service']} {alert.get('fault_type','')} merged into {deduped_alert_id}")
    return jsonify({"received": True, "alert_id": deduped_alert_id, "deduplicated": True})


@app.route("/alerts")
def get_alerts():
    limit = int(request.args.get("limit", 50))
    include_resolved = request.args.get("include_resolved", "0") == "1"
    if include_resolved:
        return jsonify(list(alerts)[:limit])
    open_alerts = [a for a in alerts if a.get("status", "OPEN") == "OPEN"]
    return jsonify(open_alerts[:limit])


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
            status = str(existing_entry.get("status", "")).upper()
            if status in ("RESOLVED", "PARTIAL"):
                _resolve_related_alerts_locked(
                    fault_type=existing_entry.get("fault_type", ""),
                    zone=existing_entry.get("zone", ""),
                    component=existing_entry.get("transformer_id", ""),
                )
                _refresh_active_alerts_count_locked()
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
            status = str(entry.get("status", "")).upper()
            if status in ("RESOLVED", "PARTIAL"):
                _resolve_related_alerts_locked(
                    fault_type=entry.get("fault_type", ""),
                    zone=entry.get("zone", ""),
                    component=entry.get("transformer_id", ""),
                )
                _refresh_active_alerts_count_locked()
        
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
            requests.get(service_url_by_port(port, "/demo/reset"), timeout=1)
        except Exception:
            pass
            
    with state_lock:
        state["is_simulating"] = False
        state["simulation_start_time"] = None
        state["system_status"] = 0
        state["active_alerts_count"] = 0
        state["resolved_alerts_count"] = 0
        state["detected_faults_total"] = 0
        state["fault_type_counts"] = _empty_fault_counts()
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
        state["resolved_alerts_count"] = 0
        state["detected_faults_total"] = 0
        state["fault_type_counts"] = _empty_fault_counts()
    return jsonify({"reset": True})


if __name__ == "__main__":
    # Clear simulation log file on start
    sim_log_path = os.path.join(ROOT, "testing", "logs", "simulation_run.txt")
    try:
        if os.path.exists(sim_log_path):
            with open(sim_log_path, "w") as f:
                f.truncate(0)
    except Exception:
        pass

    logger.info(f"Starting {SERVICE_NAME} on port {PORT} (Simulation ACTIVE by default)")
    threading.Thread(target=poll_services, daemon=True).start()
    threading.Thread(target=simulate_natural_variation, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
