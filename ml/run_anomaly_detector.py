import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ml.anomaly_detector import run_inference_loop

if __name__ == "__main__":
    run_inference_loop(poll_interval=2.0)
