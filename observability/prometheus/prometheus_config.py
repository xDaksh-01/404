"""
observability/prometheus/prometheus.yml
Prometheus scrape configuration for the Smart Grid system.
"""
# ── NOT YAML COMMENT: This file IS prometheus.yml content ──────────────────────

CONTENT = """
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'grid-controller'
    static_configs:
      - targets: ['grid-controller:5001']
    metrics_path: '/metrics'

  - job_name: 'transformer'
    static_configs:
      - targets: ['transformer:5002']
    metrics_path: '/metrics'

  - job_name: 'zone-north'
    static_configs:
      - targets: ['zone-north:5003']
    metrics_path: '/metrics'

  - job_name: 'zone-south'
    static_configs:
      - targets: ['zone-south:5004']
    metrics_path: '/metrics'

  - job_name: 'zone-east'
    static_configs:
      - targets: ['zone-east:5005']
    metrics_path: '/metrics'

  - job_name: 'zone-west'
    static_configs:
      - targets: ['zone-west:5006']
    metrics_path: '/metrics'

  - job_name: 'zone-central'
    static_configs:
      - targets: ['zone-central:5007']
    metrics_path: '/metrics'

  - job_name: 'load-balancer'
    static_configs:
      - targets: ['load-balancer:5008']
    metrics_path: '/metrics'

  - job_name: 'voltage-regulator'
    static_configs:
      - targets: ['voltage-regulator:5009']
    metrics_path: '/metrics'

  - job_name: 'fault-detection'
    static_configs:
      - targets: ['fault-detection:5010']
    metrics_path: '/metrics'
"""
