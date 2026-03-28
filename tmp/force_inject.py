import requests
import json

print("Force injecting Current Spiking...")
# Hit Zone
r1 = requests.post("http://localhost:5006/demo/inject", json={
    "type": "current_surge",
    "amps_a": 550
})
print(f"Zone response: {r1.status_code}")

# Hit Fault Detection
r2 = requests.post("http://localhost:5010/demo/inject", json={
    "type": "current_surge",
    "zone": "west",
    "feeder": "feeder-1"
})
print(f"Fault Detection response: {r2.status_code}")
