import requests
import json

print("Force injecting Current Spiking (127.0.0.1)...")
# Hit Zone
r1 = requests.post("http://127.0.0.1:5006/demo/inject", json={
    "type": "current_surge",
    "amps_a": 580
})
print(f"Zone response: {r1.status_code}")

# Hit Fault Detection
r2 = requests.post("http://127.0.0.1:5010/demo/inject", json={
    "type": "current_surge",
    "zone": "west",
    "feeder": "feeder-1"
})
print(f"Fault Detection response: {r2.status_code}")
