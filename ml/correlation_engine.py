"""
ml/correlation_engine.py
=========================
Root cause attribution using event timing and causality analysis.
Determines which component failed FIRST in a cascading sequence.
"""

import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@dataclass
class GridEvent:
    timestamp: float
    source_service: str
    component: str
    zone: str
    fault_type: str
    metric_name: str
    metric_value: float
    severity: str = "warning"


class CorrelationEngine:
    """
    Correlates events across services to identify root cause.
    Uses a time-window sliding buffer of events.
    Applies causal ordering rules for power grid physics.
    """

    # These fault types are typically root causes (not effects)
    ROOT_CAUSE_TYPES = {
        "thermal_overload",
        "cooling_fan_failure",
        "earth_fault",
        "arc_fault",
        "insulation_breakdown",
        "substation_trip",
    }

    # Typical propagation delay in seconds from cause to observable effect
    PROPAGATION_DELAYS = {
        ("thermal_overload", "voltage_instability"):  5,
        ("substation_trip",  "cascading_overload"):   3,
        ("earth_fault",      "feeder_overload"):      2,
        ("cooling_fan_failure", "thermal_overload"):  15,
        ("insulation_breakdown", "arc_fault"):        30,
    }

    def __init__(self, window_seconds: float = 60.0):
        self._window = window_seconds
        self._events: deque = deque(maxlen=500)

    def add_event(self, event: GridEvent):
        self._events.appendleft(event)

    def identify_root_cause(self, fault_type: str,
                            context: dict) -> tuple[str, str, float]:
        """
        Given detected fault_type and context, returns:
          (root_fault_type, root_component, confidence)
        """
        now = time.time()
        cutoff = now - self._window

        recent = [e for e in self._events if e.timestamp >= cutoff]
        if not recent:
            return fault_type, context.get("component", "unknown"), 0.85

        # Find earliest event that could be a root cause
        root_events = [
            e for e in recent
            if e.fault_type in self.ROOT_CAUSE_TYPES
        ]

        if root_events:
            # Earliest event is most likely root cause
            earliest = min(root_events, key=lambda e: e.timestamp)
            age = now - earliest.timestamp
            confidence = max(0.70, 1.0 - age / self._window * 0.3)
            return earliest.fault_type, earliest.component, confidence

        # If no root cause event found, use detected fault type
        return fault_type, context.get("transformer_id",
                                       context.get("feeder_id", "unknown")), 0.80

    def get_causal_chain(self) -> list:
        """Returns events sorted by time as a causal chain."""
        now = time.time()
        cutoff = now - self._window
        recent = sorted(
            [e for e in self._events if e.timestamp >= cutoff],
            key=lambda e: e.timestamp,
        )
        return [
            {
                "time": e.timestamp,
                "source": e.source_service,
                "component": e.component,
                "fault_type": e.fault_type,
                "severity": e.severity,
            }
            for e in recent
        ]


# Singleton instance
correlation_engine = CorrelationEngine()
