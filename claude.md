# Smart City Power Grid — System Documentation

## System Overview

A **Smart City Power Grid Observability & Autonomous Fault Remediation System** with 10 microservices, an ML pipeline that detects and fixes faults within 15 seconds.

```
Services running:
  • grid-controller    :5001  — SCADA hub (central coordination)
  • transformer        :5002  — 16 physical transformers
  • zone-north         :5003  — Distribution zone (peak 950MW)
  • zone-south         :5004  — Distribution zone (peak 780MW)
  • zone-east          :5005  — Distribution zone (peak 1100MW)
  • zone-west          :5006  — Distribution zone (peak 820MW)
  • zone-central       :5007  — Distribution zone (peak 1050MW)
  • load-balancer      :5008  — Power routing & emergency rebalance
  • voltage-regulator  :5009  — Tap changers, capacitor banks, reactive power
  • fault-detection    :5010  — Waveform analysis, arc/earth fault detection

Frontend:
  • React + Vite       :3000  — Dark industrial control room UI

ML Pipeline:
  • ml/feature_extractor.py   — Shared feature extraction (train + inference)
  • ml/train_model.py         — One-time training script
  • ml/anomaly_detector.py    — Real-time Isolation Forest inference
  • ml/remediation_engine.py  — HTTP action executor
  • ml/correlation_engine.py  — Root cause attribution
  • ml/decision_engine.py     — Fault → action plan map
```

---

## Quick Start

### Step 1: Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Train ML models (run ONCE, ~2 minutes)
```bash
python ml/train_model.py
```

### Step 3: Start all services
```bash
python testing/run_app.py
```

### Step 4: Start the frontend (in a new terminal)
```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:3000
```

### Step 5: Inject failures (in a 3rd terminal, while run_app.py is running)
```bash
python testing/inject_failures.py
```

---

## Fault Types Detected & Remediated

| Fault | Detection Method | Fix | Recovery Target |
|-------|-----------------|-----|-----------------|
| Thermal Overload | High load% + temp | Cool + redistribute | <85°C in 30s |
| Voltage Instability | Voltage oscillation + tap runaway | Lock tap + activate capacitors | ±6V in 15s |
| Earth Fault | Residual current spike | Isolate feeder + backup | Residual <200mA in 10s |
| Feeder Overload | Zone load >85% | Shed load + rebalance | Load <85% in 15s |
| Cascading Overload | Multiple zones overloaded | Priority load shedding | ≤1 zone overloaded in 20s |
| Substation Trip | Zone voltage/load → 0 | Restore feeders + rebalance | Substation healthy in 10s |
| Cooling Fan Failure | Rising temp, moderate load | Limit to 60% + reroute | Temp stabilizes in 30s |
| Arc Fault | Arc signature score + THD | De-energize + maintenance flag | Arc score <0.4 in 5s |
| Reactive Power Collapse | Power factor <0.85 | Max compensation + shed inductive | PF >0.88 in 15s |
| Transmission Bottleneck | Path overload + zone deficit | Alternate path + redistribute | Load within rating in 15s |

---

## ML Pipeline

### Feature Extractor (ml/feature_extractor.py)
Single source of truth for 35 features extracted from all 6 service APIs.
Both training and inference use **identical code** — no train/inference skew.

### Model 1: Isolation Forest
- Trained only on **normal operation data** (1,800 samples)
- Detects ANY anomaly, not just known faults
- Threshold: `decision_function() < 0` → anomaly

### Model 2: Random Forest Classifier
- Trained on **labeled fault data** (1,500 samples = 10 types × 150)
- Identifies root cause from anomaly patterns
- Output: fault_type string + confidence probability

### Inference Loop (every 5 seconds)
1. Collect API responses from all 10 services
2. Extract feature vector using shared extractor
3. Scale with saved StandardScaler
4. Isolation Forest detects anomaly
5. If anomaly → Random Forest classifies root cause
6. Remediation Engine executes HTTP fix actions
7. Wait 10s → verify recovery

---

## API Reference

Every service exposes:
- `GET /health` → `{"status": "online", "service": "...", "uptime_s": ...}`
- `GET /status` → service-specific JSON state
- `GET /metrics` → Prometheus text format
- `POST /demo/inject` → inject a fault scenario
- `GET /demo/reset` → reset to normal baseline

### Grid Controller specific:
- `GET /alerts` → live alert feed
- `GET /remediation-log` → ML remediation history
- `GET /metrics/summary` → aggregated dashboard summary
- `POST /alert` → receive alert from any service

---

## File Structure

```
smart-grid-system/
├── ml/
│   ├── feature_extractor.py    ← SHARED extractor (train + inference)
│   ├── train_model.py          ← Run ONCE before starting
│   ├── anomaly_detector.py     ← Real-time inference loop
│   ├── remediation_engine.py   ← HTTP action executor
│   ├── correlation_engine.py   ← Root cause attribution
│   ├── decision_engine.py      ← Fault → action map
│   └── models/
│       ├── isolation_forest.pkl
│       ├── fault_classifier.pkl
│       ├── scaler.pkl
│       └── label_encoder.pkl
├── services/
│   ├── shared/logger.py        ← Logging setup (imported by all)
│   ├── grid-controller/app.py
│   ├── transformer/app.py
│   ├── zone-{north,south,east,west,central}/
│   │   ├── app.py              ← Same template file
│   │   └── config.py           ← Zone-specific params
│   ├── load-balancer/app.py
│   ├── voltage-regulator/app.py
│   └── fault-detection/app.py
├── testing/
│   ├── run_app.py              ← Master runner
│   ├── inject_failures.py      ← 60s simulation
│   └── logs/
│       ├── simulation_run.txt  ← All events
│       └── {service}.log       ← Per-service logs
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── GridOverview.jsx
│       │   ├── TransformerPanel.jsx    ← 4×4 transformer cards
│       │   ├── ZonePanel.jsx           ← 5 zone load bars
│       │   ├── VoltagePanel.jsx        ← PF gauge, tap indicators
│       │   ├── FaultDetectionPanel.jsx ← Fault probability gauges
│       │   ├── AlertsFeed.jsx          ← Live alert stream
│       │   ├── RemediationLog.jsx      ← ML action history
│       │   ├── MetricsChart.jsx        ← Recharts line chart
│       │   └── LoadBalancerPanel.jsx   ← Path loads, shedding
│       └── services/api.js             ← All API calls
└── observability/
    └── prometheus/prometheus.yml
```

---

## Design Decisions

### Why Zone Services Share One app.py
All 5 zone services are physically identical — they just represent different geographic areas with different peak loads. Using a single `app.py` and zone-specific `config.py` eliminates 5× code duplication while keeping each zone as a truly independent process.

### Why Isolation Forest + Random Forest
- **Isolation Forest**: Detects unknown anomalies (unsupervised). Trained only on normal data, so any deviation triggers it. This means it can detect NEW fault patterns not in the training set.
- **Random Forest Classifier**: Once an anomaly is detected, this classifies WHICH known fault type it is, with confidence scores. This drives targeted remediation.

### Why Feature Extraction is Shared Code
The biggest pitfall in ML systems is **train/serve skew** — features computed differently during training vs inference. Using a single `feature_extractor.py` imported by both scripts eliminates this entirely.

### 15-Second Target Architecture
- Detection latency: ~5s (inference poll interval)
- Classification: <100ms (in-memory model)
- Remediation HTTP calls: ~300ms each × 2-3 actions = <1s
- Verification wait: 10s
- Total: ~11-12s typical, 15s maximum

---

## Troubleshooting

**"Models not found"** — Run `python ml/train_model.py` first.

**Service won't start** — Check if port is in use: `netstat -ano | findstr :500X`

**Frontend shows "Connecting..."** — Backend services must be running. Start `run_app.py` first.

**ML not detecting faults** — The Isolation Forest requires normal operation before it can identify anomalies. Let the system run for 1-2 minutes before injecting failures.
