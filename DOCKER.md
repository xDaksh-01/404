# Dockerized Smart Grid Stack

This setup runs all required components simultaneously:
- 10 backend microservices (one container each)
- ML trainer (one-shot) + anomaly detector
- Frontend (Nginx serving Vite build)
- Prometheus + Grafana

## Start

```bash
docker compose up --build
```

## Endpoints

- Frontend: http://localhost:3000
- Grid Controller API: http://localhost:5001
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)

## Stop

```bash
docker compose down
```

## Notes

- Inter-service calls use Docker DNS names via environment variables.
- `ml-trainer` runs first and writes model artifacts into `ml/models`.
- `ml-anomaly-detector` starts after trainer completion and backend health checks.
- Logs and model artifacts are persisted on host mounts:
  - `testing/logs`
  - `ml/models`
