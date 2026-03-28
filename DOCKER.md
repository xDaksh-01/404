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
- Prometheus: http://localhost:3000/prometheus
- Grafana: http://localhost:3000/grafana (admin/admin)

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
- Prometheus TSDB is persisted in Docker named volume `prometheus_data`.
- Grafana state is persisted in Docker named volume `grafana_data`.

## Observability Verification

Use this order when Prometheus/Grafana shows no data:

1. Open Prometheus targets: `http://localhost:3000/prometheus/targets`
2. Verify all jobs are `UP`
3. Try sample queries in `http://localhost:3000/prometheus/graph`:
  - `grid_load_percent`
  - `transformer_load_percent`
  - `zone_load_percent`
  - `vr_grid_power_factor_avg`
4. Open Grafana at `http://localhost:3000/grafana`
5. Confirm dashboard `Smart Grid Overview` appears automatically

If targets are `DOWN`, inspect container logs:

```bash
docker compose logs prometheus --tail=100
docker compose logs grafana --tail=100
docker compose logs grid-controller --tail=100
```
