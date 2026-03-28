"""
ml/decision_engine.py
======================
Maps fault types to prioritized remediation action plans.
Returns structured action sequences for the remediation engine.
"""

from typing import Optional

# ── Priority levels ─────────────────────────────────────────────────────────────
PRIORITY_CRITICAL   = 0
PRIORITY_HIGH       = 1
PRIORITY_MEDIUM     = 2
PRIORITY_LOW        = 3

REMEDIATION_PLANS = {
    "thermal_overload": {
        "priority": PRIORITY_CRITICAL,
        "description": "Transformer thermal overload — activate cooling and redistribute load",
        "actions": [
            {"method": "POST", "service": "transformer",
             "path": "/transformer/{transformer_id}/cooling",
             "body": {"activate": True, "fan_speed": "maximum"},
             "description": "Activate emergency cooling"},
            {"method": "POST", "service": "load_balancer",
             "path": "/emergency-rebalance",
             "body": {"zone": "{zone}", "excess_mw": 60},
             "description": "Redistribute load from overloaded transformer"},
        ],
        "verification_metric": "transformer_temperature_c",
        "verification_threshold": 85,
        "expected_recovery_seconds": 30,
    },
    "voltage_instability": {
        "priority": PRIORITY_HIGH,
        "description": "Voltage instability — lock tap changer and activate capacitors",
        "actions": [
            {"method": "POST", "service": "voltage_regulator",
             "path": "/tap-changer/lock",
             "body": {"zone": "{zone}"},
             "description": "Lock tap changer to stop hunting"},
            {"method": "POST", "service": "voltage_regulator",
             "path": "/capacitor-bank/activate",
             "body": {"zone": "{zone}"},
             "description": "Activate capacitor bank for reactive support"},
        ],
        "verification_metric": "grid_voltage_avg_v",
        "verification_threshold": 6,  # within 6V of 230V
        "expected_recovery_seconds": 15,
    },
    "earth_fault": {
        "priority": PRIORITY_CRITICAL,
        "description": "Earth fault — isolate feeder and activate backup",
        "actions": [
            {"method": "POST", "service": "zone",
             "path": "/feeder/{feeder_name}/isolate",
             "body": {},
             "description": "Isolate faulted feeder"},
            {"method": "POST", "service": "zone",
             "path": "/feeder/backup/activate",
             "body": {},
             "description": "Activate backup feeder path"},
        ],
        "verification_metric": "residual_current_ma",
        "verification_threshold": 200,
        "expected_recovery_seconds": 10,
    },
    "feeder_overload": {
        "priority": PRIORITY_HIGH,
        "description": "Feeder overload — shed load and rebalance",
        "actions": [
            {"method": "POST", "service": "zone",
             "path": "/shed-load",
             "body": {"amount_mw": 80},
             "description": "Shed 80MW from overloaded zone"},
            {"method": "POST", "service": "load_balancer",
             "path": "/emergency-rebalance",
             "body": {"zone": "{zone}", "excess_mw": 100},
             "description": "Emergency rebalance to cover deficit"},
        ],
        "verification_metric": "zone_load_percent",
        "verification_threshold": 85,
        "expected_recovery_seconds": 15,
    },
    "cascading_overload": {
        "priority": PRIORITY_CRITICAL,
        "description": "Cascading overload — activate controlled load shedding by priority",
        "actions": [
            {"method": "POST", "service": "load_balancer",
             "path": "/load-shedding/activate",
             "body": {"priority": ["industrial", "commercial", "residential"],
                      "target_reduction_mw": 300},
             "description": "Shed industrial loads first"},
            {"method": "POST", "service": "transformer",
             "path": "/emergency-reduce",
             "body": {"all_zones": True, "reduce_by_percent": 15},
             "description": "Reduce all transformer loads by 15%"},
        ],
        "verification_metric": "zones_overloaded_count",
        "verification_threshold": 1,
        "expected_recovery_seconds": 20,
    },
    "substation_trip": {
        "priority": PRIORITY_CRITICAL,
        "description": "Substation trip — restore healthy feeders and rebalance",
        "actions": [
            {"method": "POST", "service": "zone",
             "path": "/feeder/restore",
             "body": {"feeders": ["feeder-1", "feeder-3"]},
             "description": "Restore power to healthy feeders"},
            {"method": "POST", "service": "load_balancer",
             "path": "/emergency-rebalance",
             "body": {"zone": "{zone}", "mode": "restore"},
             "description": "Reroute load to cover tripped zone"},
        ],
        "verification_metric": "substation_status",
        "verification_threshold": "healthy",
        "expected_recovery_seconds": 10,
    },
    "cooling_fan_failure": {
        "priority": PRIORITY_HIGH,
        "description": "Cooling fan failure — reduce transformer load to 60%",
        "actions": [
            {"method": "POST", "service": "transformer",
             "path": "/transformer/{transformer_id}/load-limit",
             "body": {"max_load_percent": 60},
             "description": "Limit transformer to 60% load until fan repaired"},
            {"method": "POST", "service": "load_balancer",
             "path": "/reroute",
             "body": {"from_transformer": "{transformer_id}", "amount_mw": 40},
             "description": "Reroute excess load to other transformers"},
        ],
        "verification_metric": "transformer_temperature_c",
        "verification_threshold": 82,
        "expected_recovery_seconds": 30,
    },
    "arc_fault": {
        "priority": PRIORITY_CRITICAL,
        "description": "Arc fault — de-energize affected cable and flag for maintenance",
        "actions": [
            {"method": "POST", "service": "zone",
             "path": "/feeder/{feeder_name}/de-energize",
             "body": {},
             "description": "De-energize faulted cable section"},
            {"method": "POST", "service": "fault_detection",
             "path": "/feeder/{feeder_id}/flag-maintenance",
             "body": {},
             "description": "Flag feeder for urgent maintenance"},
        ],
        "verification_metric": "arc_signature_score_max",
        "verification_threshold": 0.4,
        "expected_recovery_seconds": 5,
    },
    "reactive_power_collapse": {
        "priority": PRIORITY_HIGH,
        "description": "Reactive power collapse — maximum compensation + shed inductive loads",
        "actions": [
            {"method": "POST", "service": "voltage_regulator",
             "path": "/reactive-compensation/maximum",
             "body": {"zone": "{zone}"},
             "description": "Activate maximum reactive compensation"},
            {"method": "POST", "service": "zone",
             "path": "/inductive-loads/shed",
             "body": {"target_kvar_reduction": 400},
             "description": "Shed inductive loads to restore power factor"},
        ],
        "verification_metric": "grid_power_factor_avg",
        "verification_threshold": 0.88,
        "expected_recovery_seconds": 15,
    },
    "transmission_bottleneck": {
        "priority": PRIORITY_MEDIUM,
        "description": "Transmission bottleneck — reroute via alternate path",
        "actions": [
            {"method": "POST", "service": "load_balancer",
             "path": "/reroute",
             "body": {"alternate_path": True, "split_load": True},
             "description": "Reroute power via alternate transmission path"},
            {"method": "POST", "service": "transformer",
             "path": "/distribute",
             "body": {"rebalance_type": "bottleneck_relief"},
             "description": "Redistribute transformer load for bottleneck relief"},
        ],
        "verification_metric": "load_delta_mw_total",
        "verification_threshold": 100,
        "expected_recovery_seconds": 15,
    },
}


class DecisionEngine:
    """Selects the remediation plan for a given fault type."""

    def get_plan(self, fault_type: str) -> Optional[dict]:
        """Returns the remediation plan for the fault type, or None if unknown."""
        return REMEDIATION_PLANS.get(fault_type)

    def prioritize(self, detected_faults: list) -> list:
        """Sort multiple detected faults by priority (critical first)."""
        return sorted(detected_faults,
                      key=lambda ft: REMEDIATION_PLANS.get(ft, {}).get("priority", 99))

    def get_expected_recovery_time(self, fault_type: str) -> int:
        """Returns expected recovery time in seconds."""
        plan = REMEDIATION_PLANS.get(fault_type, {})
        return plan.get("expected_recovery_seconds", 15)


# Singleton
decision_engine = DecisionEngine()
