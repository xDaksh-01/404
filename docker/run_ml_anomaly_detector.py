import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ml import anomaly_detector as detector


def host(name: str, default: str) -> str:
    return os.getenv(name, default)


hosts = {
    "grid_controller": host("GRID_CONTROLLER_HOST", "localhost"),
    "transformer": host("TRANSFORMER_HOST", "localhost"),
    "zone_north": host("ZONE_NORTH_HOST", "localhost"),
    "zone_south": host("ZONE_SOUTH_HOST", "localhost"),
    "zone_east": host("ZONE_EAST_HOST", "localhost"),
    "zone_west": host("ZONE_WEST_HOST", "localhost"),
    "zone_central": host("ZONE_CENTRAL_HOST", "localhost"),
    "load_balancer": host("LOAD_BALANCER_HOST", "localhost"),
    "voltage_regulator": host("VOLTAGE_REGULATOR_HOST", "localhost"),
    "fault_detection": host("FAULT_DETECTION_HOST", "localhost"),
}

detector.SERVICE_URLS = {
    "transformer": f"http://{hosts['transformer']}:5002/status",
    "zone_north": f"http://{hosts['zone_north']}:5003/status",
    "zone_south": f"http://{hosts['zone_south']}:5004/status",
    "zone_east": f"http://{hosts['zone_east']}:5005/status",
    "zone_west": f"http://{hosts['zone_west']}:5006/status",
    "zone_central": f"http://{hosts['zone_central']}:5007/status",
    "load_balancer": f"http://{hosts['load_balancer']}:5008/status",
    "voltage_regulator": f"http://{hosts['voltage_regulator']}:5009/status",
    "fault_detection": f"http://{hosts['fault_detection']}:5010/status",
    "grid_controller": f"http://{hosts['grid_controller']}:5001/status",
}

_original_post = detector.requests.post


def _patched_post(url, *args, **kwargs):
    if "localhost:5001" in url:
        url = url.replace("localhost:5001", f"{hosts['grid_controller']}:5001")
    return _original_post(url, *args, **kwargs)


detector.requests.post = _patched_post


if __name__ == "__main__":
    detector.run_inference_loop()
