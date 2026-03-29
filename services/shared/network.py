import os

# mapping of port -> environment variable name
SERVICE_MAP = {
    5001: "GRID_CONTROLLER_HOST",
    5002: "TRANSFORMER_HOST",
    5003: "ZONE_NORTH_HOST",
    5004: "ZONE_SOUTH_HOST",
    5005: "ZONE_EAST_HOST",
    5006: "ZONE_WEST_HOST",
    5007: "ZONE_CENTRAL_HOST",
    5008: "LOAD_BALANCER_HOST",
    5009: "VOLTAGE_REGULATOR_HOST",
    5010: "FAULT_DETECTION_HOST",
}

def get_service_url(port: int, path: str = "") -> str:
    """
    Returns the full URL for a service based on its port.
    Automatically resolves to Docker service hostnames if running in container,
    otherwise defaults to localhost.
    """
    env_var = SERVICE_MAP.get(port)
    host = "localhost"
    if env_var:
        host = os.getenv(env_var, "localhost")
    
    # Ensure path starts with /
    if path and not path.startswith("/"):
        path = "/" + path
        
    return f"http://{host}:{port}{path}"

def resolve_url(url: str) -> str:
    """
    Replaces 'localhost:PORT' in a URL string with the appropriate host for the environment.
    """
    out = url
    for port, env_var in SERVICE_MAP.items():
        host = os.getenv(env_var, "localhost")
        if f"localhost:{port}" in out:
            out = out.replace(f"localhost:{port}", f"{host}:{port}")
    return out
