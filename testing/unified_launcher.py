import os
import sys
import time
import subprocess
import webbrowser
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Colors
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def start_backend():
    # Check if backend is already running
    try:
        r = requests.get("http://localhost:5001/health", timeout=1)
        if r.status_code == 200:
            print(f"{GREEN}[BACKEND] Grid Controller already running on port 5001. Skipping startup.{RESET}")
            return None
    except:
        pass

    print(f"{CYAN}[BACKEND] Starting microservices...{RESET}")
    log_path = os.path.join(ROOT, "testing", "logs", "launcher_backend.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log_file = open(log_path, "a", encoding="utf-8")
    
    proc = subprocess.Popen(
        [sys.executable, "testing/run_app.py"],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return proc

def start_frontend():
    print(f"{CYAN}[FRONTEND] Starting React dashboard...{RESET}")
    log_path = os.path.join(ROOT, "testing", "logs", "launcher_frontend.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log_file = open(log_path, "a", encoding="utf-8")
    
    # On Windows, we use shell=True for npm
    proc = subprocess.Popen(
        "npm run dev",
        cwd=os.path.join(ROOT, "frontend"),
        shell=True,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return proc

def wait_for_backend(timeout=300):
    print(f"{YELLOW}[SYSTEM] Waiting for Grid Controller (port 5001)...{RESET}")
    start_wait = time.time()
    while time.time() - start_wait < timeout:
        try:
            r = requests.get("http://localhost:5001/health", timeout=1)
            if r.status_code == 200:
                print(f"{GREEN}[SYSTEM] Grid Controller is ONLINE.{RESET}")
                return True
        except:
            pass
        time.sleep(2)
    print(f"{RED}[ERROR] Grid Controller failed to start within {timeout}s.{RESET}")
    return False

def start_simulation_api():
    print(f"{YELLOW}[SIMULATION] Triggering autonomous failure injection...{RESET}")
    try:
        r = requests.post("http://localhost:5001/simulation/start", timeout=2)
        if r.status_code == 200:
            print(f"{GREEN}[SIMULATION] Failure injection ACTIVE.{RESET}")
            return True
    except Exception as e:
        print(f"{RED}[ERROR] Failed to start simulation: {e}{RESET}")
    return False

def main():
    print(f"\n{BOLD}{GREEN}=================================================={RESET}")
    print(f"{BOLD}{GREEN}    SMART GRID UNIFIED LAUNCHER v1.1{RESET}")
    print(f"{BOLD}{GREEN}=================================================={RESET}\n")

    back_proc = start_backend()
    front_proc = start_frontend()

    if wait_for_backend():
        # Automate the simulation start via API
        start_simulation_api()
        
        # Open browser
        time.sleep(2)
        print(f"{GREEN}[BROWSER] Opening dashboard at http://localhost:3000{RESET}")
        webbrowser.open("http://localhost:3000")
        
        print(f"\n{BOLD}System is now RUNNING.{RESET}")
        print("Check the dashboard for real-time telemetry and remediation logs.")
        print("Press Ctrl+C to shut down all components.\n")
    else:
        print(f"{RED}[FATAL] System startup failed. Cleaning up...{RESET}")
        back_proc.terminate()
        front_proc.terminate()
        return

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Shutting down...{RESET}")
        back_proc.terminate()
        front_proc.terminate()
        print(f"{GREEN}Cleanup complete.{RESET}")

if __name__ == "__main__":
    main()
