# Smart Grid Operations Guide

This guide provides instructions for starting, monitoring, and managing the containerized Smart City Power Grid system.

## 🚀 Getting Started

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+

### Deployment
To start the entire system (Frontend, 10+ Microservices, ML Engine, and Observability stack) in one go:

```powershell
docker-compose up --build -d
```

> [!IMPORTANT]
> **Initialization**: On the first run, the `ml-trainer` service will take 30-60 seconds to generate synthetic data and train the models. Other services will wait for this to complete before starting.

## 📊 Monitoring & Observability

### 1. Frontend Dashboard
Access the main grid control center at:
[http://localhost:3000](http://localhost:3000)

### 2. Grafana (Metrics & Logs)
Access advanced metrics and live logs via the **Grafana** tab in the Sidebar, or directly at:
[http://localhost:3000/grafana](http://localhost:3000/grafana)
- **User**: `admin`
- **Password**: `admin`
- **Dashboards**: Open the "Smart Grid Overview" dashboard.
- **Logs**: Scroll to the bottom of the dashboard or use the "Explore" tab with the **Loki** datasource to search logs.

### 3. Prometheus
Access raw metric targets at:
[http://localhost:3000/prometheus](http://localhost:3000/prometheus)

## 🛠️ Internal Architecture

| Service | Internal Host | Port | Description |
| :--- | :--- | :--- | :--- |
| Grid Controller | `grid-controller` | 5001 | Central API & State Aggregator |
| Transformer | `transformer` | 5002 | Physical Transformer Simulation |
| Load Balancer | `load-balancer` | 5008 | Power Routing Logic |
| Voltage Regulator | `voltage-regulator` | 5009 | Stability & Tap Control |
| Fault Detection | `fault-detection` | 5010 | Electrical Waveform Analytics |
| Zones | `zone-*` | 5003-7 | Distribution Substation Logic |
| ML Detector | `ml-anomaly-detector`| - | Real-time Inference Loop |
| Loki | `loki` | 3100 | Log Aggregation Store |

## 📁 Logging & Persistence
- **Container Logs**: Aggregated by Loki and visible in Grafana.
- **Simulation Logs**: Shared at `./testing/logs/simulation_run.txt` (mounted volume).
- **ML Models**: Persisted in `./ml/models/`.

## 🛑 Troubleshooting
- **Logs**: Run `docker-compose logs -f <service-name>` (e.g., `ml-anomaly-detector`) to see specific service stdout.
- **Port Conflicts**: Ensure ports 3000, 3001, 3100, 5001-5010, and 9090 are not in use by other local applications.
- **Reset**: To completely wipe the state and restart:
  ```powershell
  docker-compose down -v
  docker-compose up --build
  ```
