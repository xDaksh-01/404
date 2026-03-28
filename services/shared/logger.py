"""
services/shared/logger.py
=========================
Shared logging setup used by every service.
Writes to stdout + per-service log file + shared simulation_run.txt.
"""

import os
import logging
import datetime
import threading

LOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "testing", "logs")
)
os.makedirs(LOG_DIR, exist_ok=True)

SIMULATION_LOG = os.path.join(LOG_DIR, "simulation_run.txt")
_sim_log_lock = threading.Lock()


def setup_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # per-service file
    fh = logging.FileHandler(os.path.join(LOG_DIR, f"{service_name}.log"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


def write_simulation_log(service_name: str, level: str, message: str):
    now = datetime.datetime.now()
    ts = now.strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [{service_name.upper()}] [{level}] {message}\n"
    with _sim_log_lock:
        try:
            with open(SIMULATION_LOG, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
