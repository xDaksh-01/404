"""
testing/inject_failures.py
===========================
Runs for exactly 60 seconds.
Randomly injects a variety of failures every 4-6 seconds.
Shows live logs in terminal AND writes to testing/logs/simulation_run.txt.

Usage (run WHILE run_app.py is running):
    python testing/inject_failures.py
"""

import os
import sys
import time
import random
import datetime
import json
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LOG_DIR = os.path.join(ROOT, "testing", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
SIM_LOG = os.path.join(LOG_DIR, "simulation_run.txt")

# ── ANSI colors ─────────────────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA = "\033[95m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIVIDER = f"{CYAN}{'═'*60}{RESET}"

INJECTABLE_FAILURES = [
    # All 10 trained fault types with realistic injection payloads
    {
        "name": "Thermal Overload (Transformer Hot Spot)",
        "service": "transformer",
        "endpoint": "http://localhost:5002/demo/inject",
        "payload_fn": lambda: {
            "type": "thermal_overload",
            "transformer_id": f"T{random.randint(1, 16)}",
            "load_percent": random.uniform(95, 125),
            "temperature_c": random.uniform(92, 118),
        },
    },
    {
        "name": "Voltage Instability (Tap Changer Hunting)",
        "service": "voltage-regulator",
        "endpoint": "http://localhost:5009/demo/inject",
        "payload_fn": lambda: {
            "type": "voltage_instability",
            "zone": random.choice(["north", "south", "east", "west", "central"]),
            "voltage_v": random.uniform(195, 220),
            "tap_oscillation": True,
        },
    },
    {
        "name": "Earth Fault (Ground Fault on Feeder)",
        "service": "fault-detection",
        "endpoint": "http://localhost:5010/demo/inject",
        "payload_fn": lambda: {
            "type": "earth_fault",
            "feeder_id": f"feeder-{random.randint(1, 15)}",
            "residual_current_ma": random.uniform(450, 2000),
        },
    },
    {
        "name": "Feeder Overload (Zone Demand Spike)",
        "service": "zone",
        "endpoint_fn": lambda: f"http://localhost:{random.choice([5003, 5004, 5005, 5006, 5007])}/demo/inject",
        "payload_fn": lambda: {
            "type": "feeder_overload",
            "sector": f"sector-{random.randint(1, 3)}",
            "load_percent": random.uniform(90, 150),
        },
    },
    {
        "name": "Cascading Overload (Multi-Zone Crisis)",
        "service": "load-balancer",
        "endpoint": "http://localhost:5008/demo/inject",
        "payload_fn": lambda: {
            "type": "cascading_overload",
            "zones_affected": random.randint(2, 4),
            "avg_load_percent": random.uniform(90, 99),
        },
    },
    {
        "name": "Substation Trip (Offline)",
        "service": "zone",
        "endpoint_fn": lambda: f"http://localhost:{random.choice([5003, 5004, 5005, 5006, 5007])}/demo/inject",
        "payload_fn": lambda: {
            "type": "substation_trip",
            "zone": random.choice(["north", "south", "east", "west", "central"]),
        },
    },
    {
        "name": "Cooling Fan Failure (Temperature Rise)",
        "service": "transformer",
        "endpoint": "http://localhost:5002/demo/inject",
        "payload_fn": lambda: {
            "type": "cooling_fan_failure",
            "transformer_id": f"T{random.randint(1, 16)}",
            "load_percent": random.uniform(65, 85),
            "temperature_c": random.uniform(85, 98),
        },
    },
    {
        "name": "Arc Fault (Cable Insulation Breakdown)",
        "service": "fault-detection",
        "endpoint": "http://localhost:5010/demo/inject",
        "payload_fn": lambda: {
            "type": "arc_fault",
            "feeder_id": f"feeder-{random.randint(1, 15)}",
            "arc_signature_score": random.uniform(0.7, 0.99),
        },
    },
    {
        "name": "Reactive Power Collapse (PF Degradation)",
        "service": "voltage-regulator",
        "endpoint": "http://localhost:5009/demo/inject",
        "payload_fn": lambda: {
            "type": "reactive_power_collapse",
            "zone": random.choice(["north", "south", "east", "west", "central"]),
            "power_factor": random.uniform(0.65, 0.82),
        },
    },
    {
        "name": "Transmission Bottleneck (Path Overload)",
        "service": "load-balancer",
        "endpoint": "http://localhost:5008/demo/inject",
        "payload_fn": lambda: {
            "type": "transmission_bottleneck",
            "critical_path_load_percent": random.uniform(95, 165),
        },
    },
]

# ── Tracking ────────────────────────────────────────────────────────────────────
results = []


def _log(msg: str, also_print: bool = True):
    """Write to both terminal and log file."""
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    if also_print:
        print(line)
    try:
        with open(SIM_LOG, "a", encoding="utf-8") as f:
            f.write(line.replace(RED, "").replace(GREEN, "").replace(
                YELLOW, "").replace(CYAN, "").replace(MAGENTA, "").replace(
                BOLD, "").replace(RESET, "") + "\n")
    except Exception:
        pass


def inject_failure(failure: dict, t_elapsed: float) -> dict:
    """Inject a single failure and return result dict."""
    payload = failure["payload_fn"]()
    endpoint = failure.get("endpoint") or failure["endpoint_fn"]()

    _log(f"\n{DIVIDER}")
    _log(f"[T+{t_elapsed:03.0f}s] {BOLD}{YELLOW}INJECTING:{RESET} {failure['name']}")
    _log(f"         Target: {endpoint}")
    _log(f"         Payload: {json.dumps(payload)}")

    t_inject = time.time()
    inject_success = False
    try:
        r = requests.post(endpoint, json=payload, timeout=3)
        inject_success = r.status_code == 200
        status = f"{GREEN}✓ Injection successful{RESET}" if inject_success \
            else f"{RED}✗ Injection failed ({r.status_code}){RESET}"
        _log(f"         {status}")
    except Exception as e:
        _log(f"         {RED}✗ Injection error: {e}{RESET}")

    return {
        "name": failure["name"],
        "injected": inject_success,
        "inject_time": t_inject,
        "endpoint": endpoint,
        "payload": payload,
    }


def main():
    _log(f"\n{DIVIDER}")
    _log(f"{BOLD}{CYAN}SMART GRID SIMULATION - FAILURE INJECTION{RESET}")
    _log(f"Duration: 60 seconds")
    _log(f"Injection frequency: 4-6 seconds")
    _log(f"Total fault types: {len(INJECTABLE_FAILURES)}")
    _log(f"{DIVIDER}\n")

    # Wait 2 seconds before starting
    _log("Waiting 2 seconds before injection starts...")
    time.sleep(2)

    t_start = time.time()
    next_inject_time = time.time() + random.uniform(4, 6)

    while time.time() - t_start < 60:
        elapsed = time.time() - t_start

        # Should we inject now?
        if time.time() >= next_inject_time:
            failure = random.choice(INJECTABLE_FAILURES)
            result = inject_failure(failure, elapsed)
            results.append(result)
            next_inject_time = time.time() + random.uniform(4, 6)

        time.sleep(0.1)

    # Summary
    elapsed_total = time.time() - t_start
    successful = sum(1 for r in results if r["injected"])
    
    _log(f"\n{DIVIDER}")
    _log(f"{BOLD}{GREEN}SIMULATION COMPLETE{RESET}")
    _log(f"Total runtime: {elapsed_total:.1f}s")
    _log(f"Total injections: {len(results)}")
    _log(f"Successful: {successful}/{len(results)}")
    _log(f"\nFault types injected:")
    for fault_name in sorted(set(r["name"] for r in results)):
        count = sum(1 for r in results if r["name"] == fault_name)
        _log(f"  • {fault_name}: {count}x")
    _log(f"{DIVIDER}\n")


if __name__ == "__main__":
    main()
