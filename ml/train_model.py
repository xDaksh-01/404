"""
ml/train_model.py
=================
One-time training script. Run before starting the system:
    python ml/train_model.py

What it does:
1. Generates 5 minutes of synthetic normal operation data (~1800 samples)
2. Generates labeled anomaly samples for each of 10 fault types (150 each)
3. Trains Isolation Forest on normal data (anomaly detector)
4. Trains Random Forest classifier on labeled fault data (root cause ID)
5. Saves all artifacts to ml/models/
"""

import os
import sys
import time
import random
import numpy as np
import joblib

# Fix Windows console encoding for Unicode output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ─── Path setup so we can import feature_extractor ─────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ml.feature_extractor import (
    extract_features_from_simulated_state,
    features_to_vector,
    FEATURE_COLUMNS,
)

from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# ─── Constants ─────────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(ROOT, "ml", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

NORMAL_SAMPLES = 1800
FAULT_SAMPLES_PER_TYPE = 150

# Transformer config: (id, zone, capacity_mw)
TRANSFORMER_CONFIG = [
    ("T1","north",280), ("T2","north",295), ("T3","north",310),
    ("T4","south",265), ("T5","south",290),
    ("T6","east",275),  ("T7","east",285),  ("T8","east",300), ("T9","east",270),
    ("T10","west",260), ("T11","west",285),
    ("T12","central",290),("T13","central",305),("T14","central",295),
    ("T15","central",310),("T16","central",285),
]

# Zone config: (name, port, peak_mw)
ZONE_CONFIG = [
    ("north",   5003, 950),
    ("south",   5004, 780),
    ("east",    5005, 1100),
    ("west",    5006, 820),
    ("central", 5007, 1050),
]

rng = random.Random(42)

# ─── Simulation helpers ─────────────────────────────────────────────────────────

def _make_transformer(tid, zone, cap, load_pct=None, temp_override=None,
                      volt_override=None, eff_override=None,
                      oil_override=None, pf_override=None):
    if load_pct is None:
        load_pct = rng.uniform(45, 75)
    temp = temp_override if temp_override else 50 + (load_pct / 100) ** 1.8 * 50
    volt = volt_override if volt_override else 230 - (load_pct / 100) ** 1.5 * 20
    return {
        "id": tid,
        "zone": zone,
        "load_percent": load_pct,
        "temperature_c": temp,
        "voltage_output_v": volt,
        "efficiency_percent": eff_override if eff_override else rng.uniform(91, 96),
        "oil_level_percent": oil_override if oil_override else rng.uniform(92, 99),
        "power_factor": pf_override if pf_override else rng.uniform(0.91, 0.97),
    }


def _make_zone(name, peak_mw, load_pct=None, freq=None, volt=None, reactive=None,
               substation_status="healthy"):
    if load_pct is None:
        load_pct = rng.uniform(50, 75)
    return {
        "zone": name,
        "current_load_mw": peak_mw * load_pct / 100,
        "peak_load_mw": peak_mw,
        "frequency_hz": freq if freq else rng.uniform(49.9, 50.1),
        "voltage_avg_v": volt if volt else rng.uniform(227, 231),
        "reactive_power_kvar": reactive if reactive else rng.uniform(80, 200),
        "substation_status": substation_status,
    }


def _make_feeder(residual=None, thd=None, insulation=None):
    return {
        "residual_current_ma": residual if residual else rng.uniform(0, 50),
        "current_thd_percent": thd if thd else rng.uniform(2, 8),
        "insulation_resistance_mohm": insulation if insulation else rng.uniform(85, 100),
    }


def _normal_state():
    transformers = [
        _make_transformer(tid, zone, cap)
        for tid, zone, cap in TRANSFORMER_CONFIG
    ]
    zones = [_make_zone(name, peak) for name, _, peak in ZONE_CONFIG]
    return {
        "transformer": {"transformers": transformers},
        "zones": zones,
        "fault_detection": {
            "feeders": [_make_feeder() for _ in range(15)],
            "arc_signature_score_max": rng.uniform(0, 0.15),
            "fault_probability_max":   rng.uniform(0, 0.12),
        },
        "voltage_regulator": {
            "grid_voltage_avg_v":         rng.uniform(228, 231),
            "grid_voltage_min_v":         rng.uniform(225, 229),
            "grid_power_factor_avg":      rng.uniform(0.91, 0.97),
            "voltage_violations_count":   0,
            "tap_changes_per_hour":       rng.uniform(0, 3),
            "capacitor_banks_active_count": 0,
        },
        "load_balancer": {
            "total_demand_mw":           rng.uniform(3000, 3400),
            "total_allocated_mw":        rng.uniform(2980, 3420),
            "rebalance_count_session":   rng.randint(0, 2),
        },
        "grid_controller": {
            "alert_rate_per_minute":     rng.uniform(0, 0.5),
            "remediation_count_session": 0,
        },
    }


# ─── Fault state generators ────────────────────────────────────────────────────

# ─── New Basic Fault Generators ────────────────────────────────────────────────

def _voltage_overload_state():
    """Persistent high voltage across multiple zones."""
    state = _normal_state()
    v = rng.uniform(245, 258)
    for z in state["zones"]:
        z["voltage_avg_v"] = v
    state["voltage_regulator"]["grid_voltage_avg_v"] = v
    state["voltage_regulator"]["voltage_violations_count"] = 5
    return state


def _power_redistribution_state():
    """Significant load imbalance requiring grid-wide rebalancing."""
    state = _normal_state()
    # Heavily overload one zone, underload another
    state["zones"][0]["current_load_mw"] = state["zones"][0]["peak_load_mw"] * 0.98
    state["zones"][4]["current_load_mw"] = state["zones"][4]["peak_load_mw"] * 0.20
    state["load_balancer"]["rebalance_count_session"] += 5
    state["load_balancer"]["total_demand_mw"] = 4200
    return state


def _voltage_spike_state():
    """Transient high-voltage surge in a specific zone."""
    state = _normal_state()
    idx = rng.randint(0, 4)
    state["zones"][idx]["voltage_avg_v"] = rng.uniform(260, 285)
    state["voltage_regulator"]["grid_voltage_max_v"] = state["zones"][idx]["voltage_avg_v"]
    state["voltage_regulator"]["voltage_violations_count"] = 1
    return state


def _current_surge_state():
    """Sharp current spike (Current Spiking) causing feeder stress."""
    state = _normal_state()
    # Set high residual current and THD on several feeders (fields extractor reads)
    for i in rng.sample(range(15), k=rng.randint(3, 6)):
        state["fault_detection"]["feeders"][i]["residual_current_ma"] = rng.uniform(400, 2000)
        state["fault_detection"]["feeders"][i]["current_thd_percent"] = rng.uniform(20, 45)
    state["fault_detection"]["fault_probability_max"] = rng.uniform(0.75, 0.95)
    state["fault_detection"]["arc_signature_score_max"] = rng.uniform(0.3, 0.6)
    # Zone load surges too
    idx = rng.randint(0, 4)
    state["zones"][idx]["current_load_mw"] = state["zones"][idx]["peak_load_mw"] * rng.uniform(1.05, 1.15)
    state["zones"][idx]["frequency_hz"] = rng.uniform(49.3, 49.7)
    return state


def _transformer_overload_state():
    """High thermal/load levels on a specific transformer."""
    state = _normal_state()
    idx = rng.randint(0, 15)
    tid, zone, cap = TRANSFORMER_CONFIG[idx]
    state["transformer"]["transformers"][idx] = _make_transformer(
        tid, zone, cap, load_pct=rng.uniform(96, 120),
        temp_override=rng.uniform(95, 115)
    )
    return state


def _rebooting_overheat_state():
    """Component offline state resulting from thermal safety resets."""
    state = _normal_state()
    idx = rng.randint(0, 4)
    state["zones"][idx]["substation_status"] = "rebooting"
    state["zones"][idx]["current_load_mw"] = 0
    state["zones"][idx]["voltage_avg_v"] = 0
    state["grid_controller"]["system_status"] = 1 # Degraded
    return state


FAULT_GENERATORS = {
    "voltage_overload":        _voltage_overload_state,
    "power_redistribution":     _power_redistribution_state,
    "voltage_spike":           _voltage_spike_state,
    "current_surge":           _current_surge_state,
    "transformer_overload":    _transformer_overload_state,
    "rebooting_overheat":      _rebooting_overheat_state,
}


def _add_noise(vector, noise_std=0.02):
    """Add small Gaussian noise to a feature vector."""
    arr = np.array(vector, dtype=float)
    noise = np.random.normal(0, noise_std, size=arr.shape)
    return (arr + arr * noise).tolist()


# ─── Main training routine ─────────────────────────────────────────────────────

def main():
    t0 = time.time()
    bar = "=" * 60
    print(f"\n{bar}")
    print("  SMART GRID ML MODEL TRAINING")
    print("  Smart City Power Grid System")
    print(bar)

    # ── 1. Generate normal data ─────────────────────────────────────────────
    print(f"\n[{_elapsed(t0)}] Generating normal operation data...")
    normal_vectors = []
    for i in range(NORMAL_SAMPLES):
        state = _normal_state()
        fd = extract_features_from_simulated_state(state)
        normal_vectors.append(features_to_vector(fd))
    print(f"[{_elapsed(t0)}] Generated {len(normal_vectors)} normal samples")

    # ── 2. Generate fault data ──────────────────────────────────────────────
    print(f"[{_elapsed(t0)}] Generating fault scenario data...")
    fault_vectors = []
    fault_labels  = []
    for fault_name, generator in FAULT_GENERATORS.items():
        for _ in range(FAULT_SAMPLES_PER_TYPE):
            state = generator()
            fd = extract_features_from_simulated_state(state)
            vec = _add_noise(features_to_vector(fd))
            fault_vectors.append(vec)
            fault_labels.append(fault_name)
        print(f"[{_elapsed(t0)}] -> {fault_name}: {FAULT_SAMPLES_PER_TYPE} samples")

    total = len(normal_vectors) + len(fault_vectors)
    print(f"[{_elapsed(t0)}] Total dataset: {total} samples")

    # ── 3. Scale data ──────────────────────────────────────────────────────
    all_vectors = normal_vectors + fault_vectors
    scaler = StandardScaler()
    all_scaled = scaler.fit_transform(all_vectors)

    normal_scaled = all_scaled[:len(normal_vectors)]
    fault_scaled  = all_scaled[len(normal_vectors):]

    # ── 4. Train Isolation Forest ──────────────────────────────────────────
    print(f"\n[{_elapsed(t0)}] Training Isolation Forest (anomaly detector)...")
    anomaly_model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )
    anomaly_model.fit(normal_scaled)

    # Quick evaluation: normal should be +1, faults should be -1
    normal_preds = anomaly_model.predict(normal_scaled)
    fault_preds  = anomaly_model.predict(fault_scaled)
    tp_normal = np.sum(normal_preds == 1)
    tp_fault  = np.sum(fault_preds == -1)
    anom_acc  = (tp_normal + tp_fault) / (len(normal_scaled) + len(fault_scaled))
    fpr       = np.sum(normal_preds == -1) / len(normal_scaled)
    print(f"[{_elapsed(t0)}] Isolation Forest trained")
    print(f"  Anomaly detection accuracy on test set: {anom_acc*100:.1f}%")
    print(f"  False positive rate: {fpr*100:.1f}%")

    # ── 5. Train Random Forest classifier ──────────────────────────────────
    print(f"\n[{_elapsed(t0)}] Training Random Forest (fault classifier)...")
    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(fault_labels)

    X_train, X_test, y_train, y_test = train_test_split(
        fault_scaled, encoded_labels, test_size=0.2, random_state=42, stratify=encoded_labels
    )
    classifier = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )
    classifier.fit(X_train, y_train)

    y_pred = classifier.predict(X_test)
    overall_acc = accuracy_score(y_test, y_pred)
    print(f"[{_elapsed(t0)}] Fault Classifier trained")
    print(f"\nClassification Report:")
    report = classification_report(y_test, y_pred,
                                   target_names=label_encoder.classes_)
    for line in report.strip().split("\n"):
        print(f"  {line}")
    print(f"\n  Overall accuracy: {overall_acc*100:.1f}%")

    # ── 6. Save models ─────────────────────────────────────────────────────
    print(f"\n[{_elapsed(t0)}] Saving models to {MODELS_DIR}/")
    joblib.dump(anomaly_model, os.path.join(MODELS_DIR, "isolation_forest.pkl"))
    joblib.dump(classifier,   os.path.join(MODELS_DIR, "fault_classifier.pkl"))
    joblib.dump(scaler,        os.path.join(MODELS_DIR, "scaler.pkl"))
    joblib.dump(label_encoder, os.path.join(MODELS_DIR, "label_encoder.pkl"))

    # Save feature column order for verification
    import json
    with open(os.path.join(MODELS_DIR, "feature_columns.json"), "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n[{_elapsed(t0)}] Training complete in {elapsed:.1f}s. System ready to run.")
    print(f"{bar}\n")


def _elapsed(t0):
    secs = int(time.time() - t0)
    return f"{secs//60:02d}:{secs%60:02d}"


if __name__ == "__main__":
    np.random.seed(42)
    main()
