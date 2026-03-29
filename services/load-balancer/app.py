"""
services/load-balancer/app.py
==============================
Power routing intelligence. Redistributes load across zones and transformers.

CAN BREAK:
  1. Cascading Overload
  2. Transmission Bottleneck
  3. Grid Split (islanding)
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
from services.shared.network import get_service_url

app = Flask(__name__)
SERVICE_NAME = "load-balancer"
PORT = 5008
START_TIME = time.time()
logger = setup_logger(SERVICE_NAME)

ZONE_PORTS = {"north": 5003, "south": 5004, "east": 5005, "west": 5006, "central": 5007}
ZONE_PEAK_MW = {"north": 950, "south": 780, "east": 1100, "west": 820, "central": 1050}

state_lock = threading.Lock()
state = {
    "total_demand_mw":       3200.0,
    "total_allocated_mw":    3180.0,
    "total_capacity_mw":     4700.0,
    "load_balance_percent":  67.8,
    "rebalance_count_session": 0,
    "zones_overloaded_count":  0,
    "load_shedding_active":    False,
    "transmission_mode":       "normal",  # normal | bottleneck | split
    "zone_allocation": {
        "north": 0, "south": 0, "east": 0, "west": 0, "central": 0
    },
    "transmission_paths": {
        "north-central": {"rating_mw": 300, "current_mw": 120, "status": "normal"},
        "east-central":  {"rating_mw": 400, "current_mw": 200, "status": "normal"},
        "west-central":  {"rating_mw": 250, "current_mw": 100, "status": "normal"},
        "south-central": {"rating_mw": 280, "current_mw": 110, "status": "normal"},
        "east-north":    {"rating_mw": 200, "current_mw": 80,  "status": "normal"},
    },
    "load_shedding_priority": ["industrial", "commercial", "residential"],
    "shed_mw_industrial":  0,
    "shed_mw_commercial":  0,
    "shed_mw_residential": 0,
    "active_fault": None,
}


def poll_zones():
    """Every 5s: aggregate real zone loads, compute balance."""
    while True:
        try:
            total_demand = 0
            total_allocated = 0
            overloaded = 0
            allocations = {}

            for zone, port in ZONE_PORTS.items():
                try:
                    r = requests.get(get_service_url(port, "/status"), timeout=2)
                    if r.status_code == 200:
                        d = r.json()
                        demand = d.get("current_load_mw", 0)
                        lp = d.get("load_percent", 0)
                        total_demand += demand
                        
                        # Active balancing: if high, try to reduce
                        if lp > 85:
                            overloaded += 1
                            # Autonomously request rebalance
                            requests.post(get_service_url(5008, "/emergency-rebalance"), 
                                          json={"zone": zone, "mode": "reduce", "excess_mw": demand * 0.1},
                                          timeout=1)

                        allocations[zone] = round(demand, 1)
                        total_allocated += demand
                except Exception:
                    pass

            with state_lock:
                state["total_demand_mw"]    = round(total_demand, 1)
                state["total_allocated_mw"] = round(total_allocated, 1)
                state["zones_overloaded_count"] = overloaded
                state["zone_allocation"] = allocations
                if total_demand > 0:
                    state["load_balance_percent"] = round(
                        total_allocated / total_demand * 100 if total_demand > 0 else 100, 1)

                # Update transmission path loads (simulated)
                for path in state["transmission_paths"].values():
                    drift = random.gauss(0, 5)
                    path["current_mw"] = max(0, path["current_mw"] + drift)
                    load_ratio = path["current_mw"] / path["rating_mw"]
                    path["status"] = (
                        "overloaded" if load_ratio > 1.0 else
                        "warning" if load_ratio > 0.85 else
                        "normal"
                    )

            logger.debug(f"[BALANCE] Demand={total_demand:.0f}MW "
                        f"Allocated={total_allocated:.0f}MW "
                        f"Overloaded_zones={overloaded}")

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
        '# HELP lb_total_demand_mw Total power demand',
        '# TYPE lb_total_demand_mw gauge',
        f'lb_total_demand_mw {s["total_demand_mw"]}',
        '# HELP lb_zones_overloaded Number of overloaded zones',
        '# TYPE lb_zones_overloaded gauge',
        f'lb_zones_overloaded {s["zones_overloaded_count"]}',
        '# HELP lb_rebalance_count Rebalance operations this session',
        '# TYPE lb_rebalance_count counter',
        f'lb_rebalance_count {s["rebalance_count_session"]}',
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/emergency-rebalance", methods=["POST"])
def emergency_rebalance():
    data = request.get_json(force=True) or {}
    zone = data.get("zone")
    mode = data.get("mode", "reduce")
    excess_mw = data.get("excess_mw", 50)

    with state_lock:
        state["rebalance_count_session"] += 1

    if mode == "restore":
        # Try to restore zone by pulling from others
        for z, port in ZONE_PORTS.items():
            if z != zone:
                try:
                    requests.post(get_service_url(port, "/feeder/restore"),
                                  json={"feeders": [f"feeder-{i}" for i in range(1, 4)]},
                                  timeout=2)
                except Exception:
                    pass
    else:
        # Shed load from overloaded zone
        if zone and zone in ZONE_PORTS:
            try:
                requests.post(get_service_url(ZONE_PORTS[zone], "/shed-load"),
                              json={"amount_mw": excess_mw}, timeout=2)
            except Exception:
                pass

    logger.info(f"[EMERGENCY-REBALANCE] Zone={zone} mode={mode} excess={excess_mw}MW")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Emergency rebalance: zone={zone} mode={mode}")
    return jsonify({"rebalanced": True, "zone": zone, "mode": mode})


@app.route("/reroute", methods=["POST"])
def reroute():
    data = request.get_json(force=True) or {}
    alternate_path = data.get("alternate_path", False)
    split_load = data.get("split_load", False)
    from_t = data.get("from_transformer")
    amount_mw = data.get("amount_mw", 50)

    with state_lock:
        state["rebalance_count_session"] += 1
        if alternate_path:
            state["transmission_mode"] = "alternate"
        # Update transmission path loads
        for path_key, path in state["transmission_paths"].items():
            if path["status"] == "overloaded":
                path["current_mw"] = path["rating_mw"] * random.uniform(0.75, 0.85)
                path["status"] = "normal"

    rerouted_mw = amount_mw
    logger.info(f"[REROUTE] Rerouted {rerouted_mw}MW (alternate={alternate_path})")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Power rerouted {rerouted_mw}MW alternate_path={alternate_path}")
    return jsonify({"rerouted_mw": rerouted_mw, "status": "success"})


@app.route("/load-shedding/activate", methods=["POST"])
def activate_load_shedding():
    data = request.get_json(force=True) or {}
    priority = data.get("priority", ["industrial", "commercial", "residential"])
    target_mw = data.get("target_reduction_mw", 200)

    with state_lock:
        state["load_shedding_active"] = True
        remaining = target_mw
        for category in priority:
            if remaining <= 0:
                break
            shed = min(remaining, target_mw / len(priority) * random.uniform(0.8, 1.2))
            state[f"shed_mw_{category}"] = state.get(f"shed_mw_{category}", 0) + shed
            remaining -= shed

        state["total_allocated_mw"] = max(0, state["total_allocated_mw"] - target_mw)
        state["rebalance_count_session"] += 1

    # Shed from all zones
    for z, port in ZONE_PORTS.items():
        try:
            requests.post(get_service_url(port, "/shed-load"),
                          json={"amount_mw": target_mw / 5}, timeout=2)
        except Exception:
            pass

    logger.info(f"[LOAD-SHEDDING] Activated: target={target_mw}MW priority={priority}")
    write_simulation_log(SERVICE_NAME, "REMEDIATE",
                         f"Load shedding activated: {target_mw}MW priority={priority}")
    return jsonify({"shedding_active": True, "target_mw": target_mw})


@app.route("/demo/inject", methods=["POST"])
def demo_inject():
    data = request.get_json(force=True) or {}
    fault_type = data.get("type", "cascading_overload")

    with state_lock:
        state["active_fault"] = fault_type

        if fault_type == "cascading_overload":
            initial_zone = data.get("initial_zone", "central")
            cascade_zones = data.get("cascade_to", ["east", "north"])
            state["zones_overloaded_count"] = len(cascade_zones) + 1
            state["total_demand_mw"] = state["total_capacity_mw"] * random.uniform(0.94, 0.99)
            state["rebalance_count_session"] += random.randint(5, 10)

        elif fault_type == "transmission_bottleneck":
            from_zone = data.get("from_zone", "east")
            to_zone   = data.get("to_zone", "central")
            path_key  = f"{from_zone}-{to_zone}"
            if path_key in state["transmission_paths"]:
                state["transmission_paths"][path_key]["current_mw"] = data.get(
                    "actual_transfer_mw", 320)
                state["transmission_paths"][path_key]["status"] = "overloaded"
            state["transmission_mode"] = "bottleneck"

        elif fault_type == "grid_split":
            # Isolate a zone
            state["transmission_mode"] = "split"
            for path in list(state["transmission_paths"].values())[:2]:
                path["status"] = "disconnected"
                path["current_mw"] = 0

        elif fault_type == "power_redistribution":
            # Significant imbalance requiring grid-wide rebalancing
            imbalance = data.get("imbalance_mw", random.uniform(150, 300))
            state["total_demand_mw"] = state["total_allocated_mw"] + imbalance
            state["zones_overloaded_count"] = random.randint(2, 4)
            state["rebalance_count_session"] += random.randint(3, 8)
            state["load_balance_percent"] = round(
                state["total_allocated_mw"] / state["total_demand_mw"] * 100, 1)

    logger.warning(f"[INJECT] {fault_type} injected into load-balancer")
    write_simulation_log(SERVICE_NAME, "INJECT", f"{fault_type} injected into load-balancer")
    return jsonify({"injected": True, "fault_type": fault_type, "component": "load-balancer"})


@app.route("/demo/reset")
def demo_reset():
    with state_lock:
        state["load_shedding_active"] = False
        state["transmission_mode"] = "normal"
        state["zones_overloaded_count"] = 0
        state["shed_mw_industrial"] = 0
        state["shed_mw_commercial"] = 0
        state["shed_mw_residential"] = 0
        state["active_fault"] = None
        for path in state["transmission_paths"].values():
            path["status"] = "normal"
    return jsonify({"reset": True})


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {PORT}")
    threading.Thread(target=poll_zones, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
