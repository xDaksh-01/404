import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import requests
import random
import json

# Ensure stdout encoding is UTF-8 when supported (better terminal logging across platforms)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LOG_DIR = os.path.join(ROOT, "testing", "logs")

# ─── Clear previous logs on startup ───────────────────────────────────────────
if os.path.exists(LOG_DIR):
    try:
        # Delete all files and subdirectories inside LOG_DIR
        for filename in os.listdir(LOG_DIR):
            file_path = os.path.join(LOG_DIR, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
    except Exception as e:
        print(f"Warning: Could not clear logs: {e}")
        print("Hint: A previous simulation run may still be active and holding file handles. Stop running instances and retry.")

os.makedirs(LOG_DIR, exist_ok=True)
SIM_LOG = os.path.join(LOG_DIR, "simulation_run.txt")

# ── ANSI colors ─────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA = "\033[95m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CLEAR_LINE = "\033[2K\r"

SERVICES = [
    {"name": "grid-controller",  "port": 5001, "path": "services/grid-controller/app.py"},
    {"name": "transformer",       "port": 5002, "path": "services/transformer/app.py"},
    {"name": "zone-north",        "port": 5003, "path": "services/zone-north/app.py"},
    {"name": "zone-south",        "port": 5004, "path": "services/zone-south/app.py"},
    {"name": "zone-east",         "port": 5005, "path": "services/zone-east/app.py"},
    {"name": "zone-west",         "port": 5006, "path": "services/zone-west/app.py"},
    {"name": "zone-central",      "port": 5007, "path": "services/zone-central/app.py"},
    {"name": "load-balancer",     "port": 5008, "path": "services/load-balancer/app.py"},
    {"name": "voltage-regulator", "port": 5009, "path": "services/voltage-regulator/app.py"},
    {"name": "fault-detection",   "port": 5010, "path": "services/fault-detection/app.py"},
]

INJECTABLE_FAILURES = [
    {
        "name": "Voltage Overload",
        "service": "voltage-regulator",
        "endpoint": "http://localhost:5009/demo/inject",
        "payload_fn": lambda: {
            "type": "voltage_overload",
            "voltage_v": random.uniform(245, 255),
        },
    },
    {
        "name": "Power Redistribution",
        "service": "load-balancer",
        "endpoint": "http://localhost:5008/demo/inject",
        "payload_fn": lambda: {
            "type": "power_redistribution",
            "imbalance_mw": random.uniform(150, 300),
        },
    },
    {
        "name": "Voltage Spike",
        "service": "transformer",
        "endpoint": "http://localhost:5002/demo/inject",
        "payload_fn": lambda: {
            "type": "voltage_spike",
            "transformer_id": f"T{random.randint(1, 16)}",
            "voltage_v": random.uniform(265, 280),
        },
    },
    {
        "name": "Current Spiking",
        "service": "zone",
        "endpoint_fn": lambda: f"http://localhost:{random.choice([5003, 5004, 5005, 5006, 5007])}/demo/inject",
        "payload_fn": lambda: {
            "type": "current_surge",
            "amps_a": random.uniform(450, 600),
        },
    },
    {
        "name": "Transformer Overload",
        "service": "transformer",
        "endpoint": "http://localhost:5002/demo/inject",
        "payload_fn": lambda: {
            "type": "transformer_overload",
            "transformer_id": f"T{random.randint(1, 16)}",
            "load_percent": random.uniform(96, 115),
        },
    },
]

MODELS_DIR = os.path.join(ROOT, "ml", "models")
processes = []
stop_event = threading.Event()


def log(msg: str, category: str = "RUNNER"):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")
    try:
        with open(SIM_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{now}] [{category}] {msg}\n")
    except Exception:
        pass


def ensure_models():
    """Train ML models if they don't exist."""
    iso_path = os.path.join(MODELS_DIR, "isolation_forest.pkl")
    if os.path.exists(iso_path):
        log(f"{GREEN}✓{RESET} ML models found at {MODELS_DIR}")
        return

    log(f"{YELLOW}⚡ ML models not found. Training now...{RESET}")
    log("  This takes about 2-3 minutes. Please wait.")
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "ml", "train_model.py")],
        cwd=ROOT,
    )
    if result.returncode != 0:
        log(f"{RED}✗ Training failed! Check ml/train_model.py{RESET}")
        sys.exit(1)
    log(f"{GREEN}✓ ML models trained and saved.{RESET}")


def start_service(svc: dict) -> subprocess.Popen:
    """Start a service as a background subprocess."""
    script = os.path.join(ROOT, svc["path"])
    log_file = open(os.path.join(LOG_DIR, f"{svc['name']}.stdout"), "a",
                    encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [sys.executable, script],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    return proc


def health_check(port: int) -> bool:
    try:
        r = requests.get(f"http://localhost:{port}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def wait_for_services(timeout: int = 60) -> bool:
    """Poll all services until all are online or timeout."""
    t_start = time.time()
    while time.time() - t_start < timeout:
        statuses = {svc["name"]: health_check(svc["port"]) for svc in SERVICES}
        all_online = all(statuses.values())

        lines = []
        for svc in SERVICES:
            status = statuses[svc["name"]]
            icon = f"{GREEN}✓{RESET}" if status else f"{YELLOW}✗{RESET}"
            label = f"ONLINE{RESET}" if status else f"{YELLOW}STARTING...{RESET}"
            lines.append(f"  {icon} {svc['name']:<22} ({svc['port']}) - {label}")

        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\r{CLEAR_LINE}[{now}] Checking services...\n" + "\n".join(lines),
              end="", flush=True)

        if all_online:
            print()
            return True
        time.sleep(2)

    print()
    return False


def is_simulation_active() -> bool:
    """Check with grid-controller if simulation should be running logic."""
    try:
        r = requests.get("http://localhost:5001/status", timeout=1)
        if r.status_code == 200:
            return r.json().get("is_simulating", False)
    except:
        pass
    return False


def run_ml_inference():
    """Run the ML inference loop continuously in a background thread."""
    from ml.anomaly_detector import run_inference_loop
    try:
        run_inference_loop(poll_interval=2.0)  # runs forever
    except Exception as e:
        log(f"{RED}[ML-ERROR] Inference loop crashed: {e}{RESET}")


def run_failure_injection():
    """Background thread to inject randomized failures every 12-18s (avg 15s)."""
    log(f"{MAGENTA}Failure Injection Thread initialized.{RESET}", "INJECTOR")
    
    while not stop_event.is_set():
        # Wait until active
        if not is_simulation_active():
            time.sleep(2)
            continue
            
        # Frequent intervals for high visibility of rebalancing logic (4 to 8s)
        interval = random.uniform(4.0, 8.0)
        time.sleep(interval)
        
        if not is_simulation_active(): continue
        if stop_event.is_set(): break
        
        # Select random failure
        failure = random.choice(INJECTABLE_FAILURES)
        payload = failure["payload_fn"]()
        endpoint = failure.get("endpoint") or failure["endpoint_fn"]()
        
        log(f"{YELLOW}INJECTING:{RESET} {failure['name']} | Target: {endpoint}", "INJECTOR")
        
        try:
            r = requests.post(endpoint, json=payload, timeout=3)
            if r.status_code == 200:
                log(f"{GREEN}→ Injection successful{RESET} (Payload: {json.dumps(payload)})", "INJECTOR")
            else:
                log(f"{RED}→ Injection failed ({r.status_code}){RESET}", "INJECTOR")
        except Exception as e:
            log(f"{RED}→ Injection error: {e}{RESET}", "INJECTOR")


def write_simulation_header():
    now = datetime.datetime.now()
    header = (
        "=" * 80 + "\n"
        f"SMART GRID SIMULATION RUN\n"
        f"Started: {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n"
        "=" * 80 + "\n"
    )
    with open(SIM_LOG, "a", encoding="utf-8") as f:
        f.write(header)


def shutdown(sig=None, frame=None):
    log(f"\n{YELLOW}Shutting down all services...{RESET}")
    stop_event.set()
    
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    log(f"{GREEN}All services stopped. Goodbye!{RESET}")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown)

    # Write simulation log header
    write_simulation_header()

    print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
    print(f"{BOLD}{CYAN}  SMART GRID CONTROL SYSTEM{RESET}")
    print(f"{BOLD}{CYAN}  Smart City Power Grid & Autonomous Remediation{RESET}")
    print(f"{BOLD}{CYAN}{'═'*60}{RESET}\n")

    # Step 1: Ensure ML models
    ensure_models()

    # Step 2: Start all services
    log(f"Starting {len(SERVICES)} microservices...")
    for svc in SERVICES:
        proc = start_service(svc)
        processes.append(proc)
        log(f"  → {svc['name']} (port {svc['port']}) PID={proc.pid}")
        time.sleep(0.3)  # stagger startup slightly

    log("Services starting... waiting for health checks...")
    time.sleep(3)

    # Step 3: Wait for all services to be healthy
    all_online = wait_for_services(timeout=120)
    if not all_online:
        log(f"{RED}✗ Not all services came online within 90s. Check logs in {LOG_DIR}{RESET}")
        shutdown()

    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n[{now}] {GREEN}{BOLD}All {len(SERVICES)} services online. System ready.{RESET}")

    # Step 4: Start ML inference loop
    log(f"{CYAN}Starting ML inference loop (2s poll interval)...{RESET}")
    ml_thread = threading.Thread(target=run_ml_inference, daemon=True)
    ml_thread.start()

    # Step 5: Start Failure Injection Thread
    log(f"{MAGENTA}Starting Background Failure Injection...{RESET}")
    inj_thread = threading.Thread(target=run_failure_injection, daemon=True)
    inj_thread.start()

    log(f"{GREEN}Full Operational Mode: ON{RESET}")
    log(f"Log file: {SIM_LOG}")
    log(f"Frontend: http://localhost:3000")
    log(f"Press Ctrl+C to stop.\n")

    # Keep running
    while not stop_event.is_set():
        try:
            time.sleep(30)
            if not stop_event.is_set():
                online_count = sum(1 for svc in SERVICES if health_check(svc["port"]))
                log(f"[HEARTBEAT] Services online: {online_count}/{len(SERVICES)}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
