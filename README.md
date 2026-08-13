# Smart City Power Grid Observability and Autonomous Remediation

## 1. Executive Summary

This repository implements a simulated smart city power grid with:

- 10 operational grid microservices (control, distribution, balancing, voltage, and protection)
- a React frontend for live operations visibility
- an ML inference pipeline for anomaly detection and fault classification
- an autonomous remediation engine that executes corrective API actions
- an observability stack centered on Prometheus metrics and Grafana dashboards

The platform is designed to detect abnormal operating conditions, classify likely root causes, and execute service-level remediation actions without manual intervention.

This README is intentionally focused on runtime architecture, endpoint-level service documentation, ML logic, remediation logic, and observability.

---

## 2. System Topology

### 2.1 Service Topology and Ports

| Service | Port | Primary Role |
|---|---:|---|
| grid-controller | 5001 | SCADA-style coordinator, alert hub, summary API, remediation log |
| transformer | 5002 | 16-transformer fleet simulation, thermal/load controls |
| zone-north | 5003 | Distribution zone service |
| zone-south | 5004 | Distribution zone service |
| zone-east | 5005 | Distribution zone service |
| zone-west | 5006 | Distribution zone service |
| zone-central | 5007 | Distribution zone service |
| load-balancer | 5008 | Rebalancing, rerouting, and load shedding |
| voltage-regulator | 5009 | Voltage profile, tap/changer control, reactive compensation |
| fault-detection | 5010 | Feeder-level electrical fault analytics |
| ml-anomaly-detector metrics server | 5011 | ML-only Prometheus metrics endpoint |
| frontend (Vite dev server) | 3000 | Operator interface |
| Prometheus | 9090 | Metrics collection and query |
| Grafana | 3001 (typical local) | Dashboarding and analytics |

### 2.2 Functional Grouping

1. Grid supervision
- grid-controller

2. Power asset and distribution simulation
- transformer
- zone-north, zone-south, zone-east, zone-west, zone-central

3. Grid stability and balancing
- load-balancer
- voltage-regulator

4. Fault sensing and safety
- fault-detection

5. ML and automation
- ml/feature_extractor.py
- ml/train_model.py
- ml/anomaly_detector.py
- ml/correlation_engine.py
- ml/decision_engine.py
- ml/remediation_engine.py

6. Observability
- observability/prometheus/prometheus.yml
- observability/grafana/provisioning/*
- observability/grafana/dashboards/smart-grid-overview.json

---

## 3. Runtime Behavior and Data Flow

### 3.1 Control and Telemetry Loops

1. Each backend service maintains a local state model and exposes status plus metrics endpoints.
2. The grid-controller consolidates system-level information and produces an aggregated summary view.
3. The frontend periodically fetches summary and detailed endpoints for live rendering.
4. The ML detector polls service status endpoints (concurrently) and builds a unified feature vector.
5. If anomaly detection triggers, the classifier predicts a fault type and confidence score.
6. The remediation engine executes targeted API actions, then verifies recovery.
7. Results are written to remediation logs and reflected in alerts plus dashboard state.

### 3.2 ML Inference Cadence

- Poll interval: 5 seconds by default in ml/anomaly_detector.py
- Cooldown: 12 seconds per fault/component key to prevent repetitive retriggering
- Execution mode:
  - anomaly model: Isolation Forest (decision function + predict)
  - fault classifier: Random Forest probabilities

### 3.3 Verification and Escalation

The remediation engine applies a Plan-Act-Verify sequence:

1. Execute action sequence for the predicted fault class
2. Wait for a short stabilization period (3 seconds)
3. Verify via service status endpoints
4. If unresolved and still critical, escalate with reset-style action
5. Update remediation log entry and optionally resolve active alert

---

## 4. Full API Reference by Service

## 4.1 grid-controller (Port 5001)

### Core Health and State
- GET /health
  - Returns service liveness, service name, uptime.
- GET /status
  - Returns internal controller state.
- GET /metrics
  - Prometheus exposition for aggregate grid metrics.
- GET /metrics/summary
  - Aggregated payload used by frontend; includes transformer/load-balancer/voltage snapshots and derived risk labels.

### Alerts and Incident Management
- POST /alert
  - Adds an alert entry into controller alert stream.
- GET /alerts
  - Query alert feed with optional limit and resolved filter.
- POST /alerts/resolve
  - Resolves best-matching unresolved alert.

### Remediation Audit Trail
- GET /remediation-log
  - Returns remediation events (most recent first, optional limit).
- POST /remediation-log
  - Creates or updates remediation records.

### Simulation Session Controls
- POST /simulation/start
  - Enables simulation mode and starts session timer.
- POST /simulation/stop
  - Stops simulation and triggers reset fan-out to all participating services.

### Demo Fault Testing
- POST /demo/inject
  - Injects synthetic controller-level behavior anomalies.
- GET /demo/reset
  - Resets controller to baseline healthy state and marks alerts resolved.

---

## 4.2 transformer (Port 5002)

### Core Health and Fleet Views
- GET /health
- GET /status
  - Returns all simulated transformers (with selected fields sanitized for response size).
- GET /transformer/<tid>
  - Returns a single transformer object by ID.
- GET /metrics
  - Prometheus gauges for per-transformer load and temperature.

### Operational Controls
- POST /transformer/<tid>/cooling
  - Activates/deactivates cooling with optional fan-speed semantics.
  - Includes immediate thermal relief behavior when activated.
- POST /transformer/<tid>/load-limit
  - Applies max load cap and clamps current load if above threshold.
- POST /emergency-reduce
  - Fleet or scoped load reduction with thermal relief.
- POST /distribute
  - Rebalances high-load transformers toward fleet average.

### Demo Fault Testing
- POST /demo/inject
  - Supports synthetic faults such as thermal_overload, cooling_fan_failure, voltage_instability, voltage_spike, and oil_degradation.
- GET /demo/reset
  - Resets all transformers to baseline profile.

---

## 4.3 Zone Services (Ports 5003 to 5007)

Applies to all of:
- zone-north (5003)
- zone-south (5004)
- zone-east (5005)
- zone-west (5006)
- zone-central (5007)

All zone services expose the same endpoint contract.

### Core Health and State
- GET /health
- GET /status
- GET /metrics
  - Prometheus gauges for zone load percent, frequency, and average voltage.

### Distribution and Feeder Controls
- POST /shed-load
  - Sheds demand in zone sectors.
- POST /feeder/<feeder_id>/isolate
  - Isolates an affected feeder and reduces zone load.
- POST /feeder/backup/activate
  - Activates backup path for isolated feeders.
- POST /feeder/restore
  - Restores targeted feeders and can recover tripped substation state.
- POST /feeder/<feeder_id>/de-energize
  - Hard de-energize action for severe feeder faults.

### Voltage and Reactive Controls
- POST /capacitor-bank/activate
  - Enables local capacitor compensation.
- POST /inductive-loads/shed
  - Reduces inductive reactive burden to improve PF.
- POST /tap-change
  - Adjusts zone voltage offset via tap position.

### Demo Fault Testing
- POST /demo/inject
  - Simulates feeder_overload, frequency_deviation, current_surge, and related fault conditions.
- GET /demo/reset
  - Restores healthy feeder/substation and nominal values.

---

## 4.4 load-balancer (Port 5008)

### Core Health and State
- GET /health
- GET /status
- GET /metrics
  - Prometheus metrics for demand, overloaded zone count, and rebalance counters.

### Balancing Controls
- POST /emergency-rebalance
  - Rebalance by zone in reduce or restore modes.
  - Coordinates with zone feeder endpoints as needed.
- POST /reroute
  - Adjusts routing strategy including alternate paths and split load behavior.
- POST /load-shedding/activate
  - Priority-based demand shedding across categories and zones.

### Demo Fault Testing
- POST /demo/inject
  - Simulates cascading_overload, transmission_bottleneck, grid_split, and power_redistribution cases.
- GET /demo/reset
  - Clears shedding and restores normal transmission mode.

---

## 4.5 voltage-regulator (Port 5009)

### Core Health and State
- GET /health
- GET /status
- GET /metrics
  - Exposes grid voltage, power factor, violation count, and tap activity metrics.

### Voltage and Compensation Controls
- POST /tap-changer/lock
  - Locks tap changer to prevent oscillatory hunting.
- POST /tap-changer/unlock
  - Unlocks tap changer.
- POST /capacitor-bank/activate
  - Activates capacitor bank support (zone-aware).
- POST /capacitor-bank/deactivate
  - Deactivates selected zone bank or all banks.
- POST /reactive-compensation/maximum
  - Max compensation mode for rapid PF recovery.

### Demo Fault Testing
- POST /demo/inject
  - Simulates voltage_instability, voltage_overload, reactive_power_collapse, and voltage_profile_violation.
- GET /demo/reset
  - Restores normal regulation state.

---

## 4.6 fault-detection (Port 5010)

### Core Health and State
- GET /health
- GET /status
- GET /metrics
  - Prometheus metrics for fault probability, arc signature, active faults, and residual current maxima.

### Safety and Maintenance
- POST /feeder/<feeder_id>/flag-maintenance
  - Marks feeder for maintenance workflow.

### Demo Fault Testing
- POST /demo/inject
  - Simulates earth_fault, short_circuit, arc_fault, insulation_breakdown on selected feeder context.
- GET /demo/reset
  - Clears active feeder fault state to healthy baseline.

---

## 4.7 ML Detector Metrics Service (Port 5011)

Exposed by ml/anomaly_detector.py through a lightweight Flask app.

- GET /health
  - Health indicator for ml-anomaly-detector metrics service.
- GET /metrics
  - Prometheus counter: ml_detected_faults_total{fault_type="..."}

---

## 5. ML Services: Detailed Technical Report

## 5.1 feature_extractor.py (Single Source of Features)

Purpose:
- Converts heterogeneous service API responses into a fixed-order feature vector.
- Guarantees consistent feature ordering between training and runtime inference.

Feature set:
- Declares FEATURE_COLUMNS for transformer, zone, fault, voltage, load-balancer, and controller aggregates.
- Supports conversion from both live API payloads and simulated training states.

Design impact:
- Prevents train/serve feature drift.
- Enables deterministic model input schema.

## 5.2 train_model.py (Offline Training Script)

Training data generation:
- normal samples: 1800
- fault samples: 150 per fault type
- supported generated fault labels include:
  - voltage_overload
  - power_redistribution
  - voltage_spike
  - current_surge
  - transformer_overload
  - rebooting_overheat

Model stack:
- IsolationForest for anomaly detection on normal-state embeddings
- RandomForestClassifier for fault class prediction
- StandardScaler for normalization
- LabelEncoder for class index mapping

Persisted artifacts under ml/models:
- isolation_forest.pkl
- fault_classifier.pkl
- scaler.pkl
- label_encoder.pkl
- feature_columns.json

## 5.3 anomaly_detector.py (Realtime Inference and Triggering)

Responsibilities:
1. Poll all service /status endpoints concurrently.
2. Build feature vector via shared extractor.
3. Scale vector with persisted scaler.
4. Run anomaly detector.
5. On anomaly, classify fault type and confidence.
6. Build component context (zone, transformer, feeder heuristic).
7. Enforce per-component cooldown.
8. Push alert to grid-controller.
9. Invoke remediation_engine.fix(fault_type, context).
10. Export ML counters to Prometheus.

Operational details:
- inference loop default cadence is 5 seconds
- cooldown key pattern resembles fault_type:component
- model files are auto-trained at runtime if missing

## 5.4 correlation_engine.py (Root Cause Attribution Support)

Purpose:
- Maintains event buffer over sliding time window.
- Applies known root-cause-type preferences and propagation assumptions.

Key concepts:
- ROOT_CAUSE_TYPES: prioritized likely-origin fault classes
- PROPAGATION_DELAYS: expected causal lag mappings between cause/effect pairs
- identify_root_cause(...) returns tuple:
  - root_fault_type
  - root_component
  - confidence

## 5.5 decision_engine.py (Plan Selection)

Purpose:
- Maps known fault types to structured remediation plans including:
  - priority level
  - ordered actions
  - verification metric
  - verification threshold
  - expected recovery target

Current plan catalog:
- thermal_overload
- voltage_instability
- earth_fault
- feeder_overload
- cascading_overload
- substation_trip
- cooling_fan_failure
- arc_fault
- reactive_power_collapse
- transmission_bottleneck

Priority model:
- critical: 0
- high: 1
- medium: 2
- low: 3

## 5.6 remediation_engine.py (Execution and Closed Loop Verification)

Core method:
- fix(fault_type, context)

High-level behavior:
1. Build remediation_id and context defaults.
2. Select fault-specific action branch.
3. Execute HTTP POST/GET actions with timing and logs.
4. Write initial remediation record to grid-controller.
5. Wait 3 seconds and verify fault clearance.
6. If unresolved and still severe, apply escalation/reset logic.
7. Update remediation record with final status.
8. Resolve corresponding active alert when status is RESOLVED.

Status outcomes:
- RESOLVED
- UNRESOLVED
- EXCEEDED

Verification paths are fault-dependent and query service endpoints like:
- transformer state for thermal/load recovery
- voltage-regulator state for voltage recovery
- fault-detection state for residual current recovery
- load-balancer state for overload convergence
- zone status for rebooting-overheat stabilization

---

## 6. Remediation Logic Reference by Fault Family

## 6.1 Transformer and Thermal Cases

- transformer_overload:
  - conditional severity-aware path:
    - mild: cooling strategy
    - medium: cooling + emergency reduction
    - severe: cooling + emergency reduction + component reset

- cooling_fan_failure:
  - enforce load limit
  - reroute excess load via load-balancer

## 6.2 Voltage Quality Cases

- voltage_overload or voltage_spike:
  - lock tap changer
  - deactivate capacitor bank for surge protection path
  - verify voltage approaches acceptable band

- reactive_power_collapse:
  - activate maximum reactive compensation
  - shed inductive loads in affected zone

## 6.3 Feeder and Protection Cases

- current_surge:
  - heavy zone load shedding
  - emergency zone rebalance

- arc/earth style protection methods exist in engine helpers:
  - feeder isolate and backup activation
  - feeder de-energize and maintenance flagging

## 6.4 Grid-Level Redistribution Cases

- power_redistribution:
  - route choice depends on overloaded_zones severity
  - can escalate to emergency grid balancing helpers

- rebooting_overheat:
  - component reset path for safety-critical stabilization

---

## 7. Prometheus Report

Prometheus configuration source:
- observability/prometheus/prometheus.yml

Global timings:
- scrape_interval: 5s
- evaluation_interval: 5s

Configured jobs:
- grid-controller at localhost:5001/metrics
- transformer at localhost:5002/metrics
- zone-north at localhost:5003/metrics
- zone-south at localhost:5004/metrics
- zone-east at localhost:5005/metrics
- zone-west at localhost:5006/metrics
- zone-central at localhost:5007/metrics
- load-balancer at localhost:5008/metrics
- voltage-regulator at localhost:5009/metrics
- fault-detection at localhost:5010/metrics
- ml-anomaly-detector at ml-anomaly-detector:5011/metrics

Representative metric families by service:
- grid-controller:
  - grid_total_load_mw
  - grid_capacity_mw
  - grid_load_percent
  - active_alerts_count
  - services_online_count
  - remediation_actions_count

- transformer:
  - transformer_load_percent{ id, zone }
  - transformer_temperature_c{ id, zone }

- zone services:
  - zone_load_percent{ zone }
  - zone_frequency_hz{ zone }
  - zone_voltage_v{ zone }

- load-balancer:
  - lb_total_demand_mw
  - lb_zones_overloaded
  - lb_rebalance_count

- voltage-regulator:
  - vr_grid_voltage_avg_v
  - vr_grid_power_factor_avg
  - vr_voltage_violations_count
  - vr_tap_changes_per_hour

- fault-detection:
  - fd_fault_probability_max
  - fd_arc_signature_score_max
  - fd_active_faults_count
  - fd_residual_current_ma_max

- ML metrics service:
  - ml_detected_faults_total{ fault_type }

---

## 8. Grafana Report

Grafana provisioning sources:
- observability/grafana/provisioning/datasources/prometheus.yml
- observability/grafana/provisioning/dashboards/dashboards.yml
- observability/grafana/dashboards/smart-grid-overview.json

### 8.1 Datasource Configuration

Default datasource:
- name: Prometheus
- type: prometheus
- URL: http://localhost:9090
- access: proxy
- editable: true

### 8.2 Dashboard Provider Configuration

Provider details:
- provider name: SmartGridDashboards
- folder: Smart Grid
- updateIntervalSeconds: 10
- filesystem source path points to observability/grafana/dashboards

### 8.3 Dashboard Purpose

The smart-grid-overview dashboard is intended to provide:
- live operational health indicators
- fault and remediation trends
- service-level metrics correlation
- operator-facing diagnosis context for active incidents

---

## 9. Local Run Procedure

## 9.1 Backend and ML Dependencies

Install Python requirements from repository root:

```bash
pip install -r requirements.txt
```

Optional ML-specific requirements file:

```bash
pip install -r ml/requirements.txt
```

## 9.2 Train Models (Recommended before first inference run)

```bash
python ml/train_model.py
```

## 9.3 Start Backend Services and ML Loop

```bash
python testing/run_app.py
```

## 9.4 Start Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## 9.5 Start Prometheus and Grafana (Local Binaries/Install)

Prometheus:

```powershell
Set-Location <repo-root>
<path-to-prometheus-exe> --config.file="<repo-root>/observability/prometheus/prometheus.yml" --web.listen-address=":9090"
```

Grafana:

```powershell
Set-Location "<grafana-install-home>"
$env:GF_SERVER_HTTP_PORT="3001"
$env:GF_SECURITY_ADMIN_USER="admin"
$env:GF_SECURITY_ADMIN_PASSWORD="admin"
$env:GF_PATHS_PROVISIONING="<repo-root>/observability/grafana/provisioning"
<path-to-grafana-server-exe> --homepath "<grafana-install-home>"
```

## 9.6 Verify Interfaces

- Frontend: http://localhost:3000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

---

## 10. Validation and Troubleshooting Checklist

1. If frontend shows stale/no data:
- verify grid-controller /metrics/summary is reachable on port 5001
- verify run_app process is alive

2. If no ML fault events appear:
- verify models exist in ml/models
- verify ml-anomaly-detector inference loop is running
- verify Prometheus can scrape ML metrics endpoint

3. If remediation log is empty:
- verify POST /remediation-log on grid-controller is reachable
- inspect testing/logs for remediation-engine actions and failures

4. If Prometheus has missing targets:
- open Prometheus targets page and inspect failed jobs
- confirm each service /metrics endpoint responds with plain text exposition

5. If Grafana panels are empty:
- verify Prometheus datasource URL is reachable from Grafana
- confirm dashboard provider path points to existing dashboard JSON

---

## 11. Repository Pointers

Core backend services:
- services/grid-controller/app.py
- services/transformer/app.py
- services/zone-*/app.py
- services/load-balancer/app.py
- services/voltage-regulator/app.py
- services/fault-detection/app.py

ML and automation:
- ml/feature_extractor.py
- ml/train_model.py
- ml/anomaly_detector.py
- ml/decision_engine.py
- ml/correlation_engine.py
- ml/remediation_engine.py

Frontend integration:
- frontend/src/services/api.js
- frontend/src/pages/SystemOverview.jsx

Observability:
- observability/prometheus/prometheus.yml
- observability/grafana/provisioning/datasources/prometheus.yml
- observability/grafana/provisioning/dashboards/dashboards.yml
- observability/grafana/dashboards/smart-grid-overview.json

---

This README is intended to serve as a detailed operational and engineering report for developers, reviewers, and operators working on the Smart City Power Grid platform.
