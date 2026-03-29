"""
ml/anomaly_detector.py
=======================
Real-time ML inference loop.
Loads trained models, polls all services every 5s,
detects anomalies, classifies root cause, triggers remediation.
"""

import os
import sys
import time
import json
import logging
import threading

import numpy as np
import joblib
import requests
from flask import Flask, Response, jsonify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ml.feature_extractor import (
    extract_features_from_api_responses,
    features_to_vector,
    FEATURE_COLUMNS,
)
from services.shared.logger import setup_logger, write_simulation_log
from services.shared.network import get_service_url, resolve_url

logger = setup_logger("ml-anomaly-detector")

MODELS_DIR = os.path.join(ROOT, "ml", "models")

SERVICE_URLS = {
    "transformer":       get_service_url(5002, "/status"),
    "zone_north":        get_service_url(5003, "/status"),
    "zone_south":        get_service_url(5004, "/status"),
    "zone_east":         get_service_url(5005, "/status"),
    "zone_west":         get_service_url(5006, "/status"),
    "zone_central":      get_service_url(5007, "/status"),
    "load_balancer":     get_service_url(5008, "/status"),
    "voltage_regulator": get_service_url(5009, "/status"),
    "fault_detection":   get_service_url(5010, "/status"),
    "grid_controller":   get_service_url(5001, "/status"),
}

from concurrent.futures import ThreadPoolExecutor

ANOMALY_COOLDOWN = 12  # Reduced to allow faster re-triggering
_last_anomaly_times = {} # component_key -> timestamp
_cooldown_lock = threading.Lock()

# ─── Metrics Exposition ────────────────────────────────────────────────────────
metrics_app = Flask(__name__)
fault_counts = {} # fault_type -> count
metrics_lock = threading.Lock()

@metrics_app.route("/metrics")
def get_metrics():
    with metrics_lock:
        lines = [
            '# HELP ml_detected_faults_total Total count of detected faults by type',
            '# TYPE ml_detected_faults_total counter'
        ]
        for ftype, count in fault_counts.items():
            lines.append(f'ml_detected_faults_total{{fault_type="{ftype}"}} {count}')
        return Response("\n".join(lines) + "\n", mimetype="text/plain")

@metrics_app.route("/health")
def ml_health():
    return jsonify({"status": "healthy", "service": "ml-anomaly-detector"})

def start_metrics_server():
    logger.info("[METRICS] Starting ML metrics server on port 5011")
    metrics_app.run(host="0.0.0.0", port=5011, debug=False, use_reloader=False)

def increment_fault_counter(fault_type):
    with metrics_lock:
        fault_counts[fault_type] = fault_counts.get(fault_type, 0) + 1


def load_models():
    """Load models OR train them if missing."""
    model_path = os.path.join(MODELS_DIR, "isolation_forest.pkl")

    if not os.path.exists(model_path):
        logger.warning("[ML] Models not found. Training at runtime...")

        from ml.train_model import main as train_main
        train_main()

    anomaly_model  = joblib.load(os.path.join(MODELS_DIR, "isolation_forest.pkl"))
    classifier     = joblib.load(os.path.join(MODELS_DIR, "fault_classifier.pkl"))
    scaler         = joblib.load(os.path.join(MODELS_DIR, "scaler.pkl"))
    label_encoder  = joblib.load(os.path.join(MODELS_DIR, "label_encoder.pkl"))

    logger.info("[ML] Models ready (runtime trained or loaded)")
    return anomaly_model, classifier, scaler, label_encoder


def collect_metrics() -> dict:
    """Fetch status from all services concurrently to reduce latency."""
    responses = {}

    def fetch(service, url):
        try:
            r = requests.get(url, timeout=1.5)
            if r.status_code == 200:
                return service, r.json()
        except Exception:
            pass
        return service, {}

    with ThreadPoolExecutor(max_workers=len(SERVICE_URLS)) as executor:
        futs = [executor.submit(fetch, s, u) for s, u in SERVICE_URLS.items()]
        for f in futs:
            s, data = f.result()
            responses[s] = data

    return responses


def build_feature_vector(responses: dict) -> np.ndarray:
    """Convert API responses → feature vector using the shared extractor."""
    zone_responses = [
        responses.get("zone_north",   {}),
        responses.get("zone_south",   {}),
        responses.get("zone_east",    {}),
        responses.get("zone_west",    {}),
        responses.get("zone_central", {}),
    ]
    feature_dict = extract_features_from_api_responses(
        transformer_response=    responses.get("transformer",       {}),
        zone_responses=          zone_responses,
        fault_response=          responses.get("fault_detection",   {}),
        voltage_response=        responses.get("voltage_regulator", {}),
        loadbalancer_response=   responses.get("load_balancer",     {}),
        gridcontroller_response= responses.get("grid_controller",   {}),
    )
    return np.array(features_to_vector(feature_dict), dtype=float)


def identify_affected_components(responses: dict, fault_type: str) -> dict:
    """
    Heuristic root cause location based on which service's metrics
    are most anomalous for this fault type.
    Returns {"zone": ..., "transformer_id": ..., "feeder": ...}
    """
    context = {}

    # Identify worst transformer
    transformers = responses.get("transformer", {}).get("transformers", [])
    if transformers:
        worst_t = max(transformers, key=lambda t: t.get("load_percent", 0))
        context["transformer_id"] = worst_t.get("id", "T3")
        context["transformer_zone"] = worst_t.get("zone", "central")

    # Identify worst zone
    zone_data = {
        "north":   responses.get("zone_north",   {}),
        "south":   responses.get("zone_south",   {}),
        "east":    responses.get("zone_east",    {}),
        "west":    responses.get("zone_west",    {}),
        "central": responses.get("zone_central", {}),
    }
    worst_z = max(zone_data.items(),
                  key=lambda kv: kv[1].get("load_percent", 0))
    context["zone"] = worst_z[0]

    # Identify worst feeder
    feeders = responses.get("fault_detection", {}).get("feeders", [])
    if feeders:
        worst_f = max(feeders, key=lambda f: f.get("residual_current_ma", 0))
        context["feeder_id"] = worst_f.get("feeder_id", "central-feeder-1")
        feeder_zone = worst_f.get("zone", "central")
        context["zone"] = feeder_zone

    return context


def run_inference_loop(poll_interval: float = 5.0, once: bool = False):
    """
    Main ML inference loop. Runs forever (default) or once.
    1. Collect metrics → 2. Build feature vector →
    3. Anomaly detection → 4. Root cause classification →
    5. Trigger remediation
    """
    anomaly_model, classifier, scaler, label_encoder = load_models()
    logger.info("[INFERENCE] ML inference loop starting...")
    write_simulation_log("ml-anomaly-detector", "INFO", "Inference loop started")

    from ml.remediation_engine import RemediationEngine
    remediation_engine = RemediationEngine()

    while True:
        loop_start = time.time()

        try:
            # ── 1. Collect ────────────────────────────────────────────────
            responses = collect_metrics()

            # ── 2. Feature vector ─────────────────────────────────────────
            vec = build_feature_vector(responses)
            vec_scaled = scaler.transform([vec])

            # ── 3. Anomaly detection ──────────────────────────────────────
            anomaly_score = float(anomaly_model.decision_function(vec_scaled)[0])
            prediction    = anomaly_model.predict(vec_scaled)[0]
            is_anomaly    = (prediction == -1)

            if is_anomaly:
                # ── 4. Classify root cause ────────────────────────────────
                fault_proba = classifier.predict_proba(vec_scaled)[0]
                fault_idx   = np.argmax(fault_proba)
                fault_type  = label_encoder.classes_[fault_idx]
                confidence  = float(fault_proba[fault_idx])

                context = identify_affected_components(responses, fault_type)
                
                # Determine component key for cooldown
                comp_id = context.get("transformer_id") or context.get("zone") or "global"
                comp_key = f"{fault_type}:{comp_id}"

                with _cooldown_lock:
                    now = time.time()
                    last_time = _last_anomaly_times.get(comp_key, 0)
                    if now - last_time < ANOMALY_COOLDOWN:
                        if once: return
                        time.sleep(poll_interval)
                        continue
                    _last_anomaly_times[comp_key] = now

                logger.warning(
    f"""
ANOMALY DETECTED
Score: {anomaly_score:.4f}
Root Cause: {fault_type}
Confidence: {confidence:.2f}
Context: {context}
⚡ Auto-Healing Triggered
"""
)
                increment_fault_counter(fault_type)
                write_simulation_log("ml-anomaly-detector", "ML-DETECT",
                    f"Anomaly detected score={anomaly_score:.4f} prediction={prediction}")
                write_simulation_log("ml-anomaly-detector", "ML-CLASSIFY",
                    f"Root cause={fault_type} confidence={confidence:.2f} context={context}")

                # Map fault types to human-readable labels for the dashboard
                display_names = {
                    "current_surge": "Critical Current Spike",
                    "voltage_overload": "Sustained Voltage Overload",
                    "transformer_overload": "Transformer Thermal Overload",
                    "power_redistribution": "Grid-wide Load Rebalancing",
                    "voltage_spike": "Unexpected Voltage Spike",
                    "rebooting_overheat": "Substation Overheating"
                }
                display_name = display_names.get(fault_type, fault_type.replace('_', ' ').capitalize())

                # Post to grid controller alert log
                try:
                    requests.post(get_service_url(5001, "/alert"), json={
                        "severity": "CRITICAL",
                        "service":  "ml-anomaly-detector",
                        "fault_type": fault_type,
                        "message": f"Autonomous detection of {display_name}",
                        "zone":      context.get("zone", ""),
                        "component": context.get("transformer_id",
                                                 context.get("feeder_id", "")),
                    }, timeout=2)
                except Exception:
                    pass

                # ── 5. Execute remediation ────────────────────────────────
                remediation_engine.fix(fault_type, context)

            if once: break

            # Maintain poll interval
            elapsed = time.time() - loop_start
            wait = max(0.1, poll_interval - elapsed)
            time.sleep(wait)

        except Exception as e:
            logger.error(f"[INFERENCE-ERROR] {e}")
            if once: break
            time.sleep(2)


if __name__ == "__main__":
    threading.Thread(target=start_metrics_server, daemon=True).start()
    run_inference_loop()
