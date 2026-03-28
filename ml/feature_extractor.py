"""
ml/feature_extractor.py
=======================
Single source of truth for converting raw service API responses
into the feature vector used by both training and inference.

Imported by:
- ml/train_model.py  (training time)
- ml/anomaly_detector.py  (inference time)
"""

FEATURE_COLUMNS = [
    # Transformer metrics (aggregated across all 16)
    "transformer_load_percent_avg",
    "transformer_load_percent_max",
    "transformer_temperature_avg",
    "transformer_temperature_max",
    "transformer_voltage_avg",
    "transformer_efficiency_avg",
    "transformer_oil_level_min",
    "transformer_power_factor_avg",
    "transformers_overloaded_count",
    "transformers_critical_count",

    # Zone metrics (aggregated across all 5 zones)
    "zone_load_mw_total",
    "zone_load_percent_avg",
    "zone_load_percent_max",
    "zone_frequency_avg",
    "zone_frequency_min",
    "zone_voltage_avg",
    "zone_voltage_min",
    "zone_reactive_power_total",
    "zones_overloaded_count",
    "zones_tripped_count",

    # Fault detection metrics
    "residual_current_ma_max",
    "current_thd_percent_avg",
    "insulation_resistance_min",
    "arc_signature_score_max",
    "fault_probability_max",

    # Voltage regulator metrics
    "grid_voltage_avg",
    "grid_voltage_min",
    "grid_power_factor_avg",
    "voltage_violations_count",
    "tap_changes_per_hour",
    "capacitor_banks_active_count",

    # Load balancer metrics
    "load_delta_mw_total",
    "rebalance_count_session",

    # Grid controller metrics
    "alert_rate_per_minute",
    "remediation_count_session",
]


def extract_features_from_api_responses(
    transformer_response: dict,
    zone_responses: list,
    fault_response: dict,
    voltage_response: dict,
    loadbalancer_response: dict,
    gridcontroller_response: dict,
) -> dict:
    """
    Called at INFERENCE TIME by anomaly_detector.py.
    Takes raw API /status responses, returns normalized feature dict.
    """
    transformers = transformer_response.get("transformers", [])

    loads       = [t.get("load_percent", 0) for t in transformers]
    temps       = [t.get("temperature_c", 60) for t in transformers]
    voltages    = [t.get("voltage_output_v", 230) for t in transformers]
    efficiencies= [t.get("efficiency_percent", 93) for t in transformers]
    oil_levels  = [t.get("oil_level_percent", 95) for t in transformers]
    power_factors = [t.get("power_factor", 0.94) for t in transformers]

    zone_loads_mw   = [z.get("current_load_mw", 0) for z in zone_responses]
    zone_peak_mw    = [z.get("peak_load_mw", 1000) for z in zone_responses]
    zone_load_pcts  = [
        (zone_loads_mw[i] / zone_peak_mw[i] * 100) if zone_peak_mw[i] > 0 else 0
        for i in range(len(zone_responses))
    ]
    zone_freqs      = [z.get("frequency_hz", 50.0) for z in zone_responses]
    zone_volts      = [z.get("voltage_avg_v", 230) for z in zone_responses]
    zone_reactive   = [z.get("reactive_power_kvar", 100) for z in zone_responses]

    feeders     = fault_response.get("feeders", [])
    residuals   = [f.get("residual_current_ma", 0) for f in feeders]
    thds        = [f.get("current_thd_percent", 3) for f in feeders]
    insulations = [f.get("insulation_resistance_mohm", 95) for f in feeders]

    vr = voltage_response    if voltage_response    else {}
    lb = loadbalancer_response if loadbalancer_response else {}
    gc = gridcontroller_response if gridcontroller_response else {}

    total_demand    = lb.get("total_demand_mw", 3200)
    total_allocated = lb.get("total_allocated_mw", 3200)

    return {
        "transformer_load_percent_avg":  safe_avg(loads),
        "transformer_load_percent_max":  safe_max(loads),
        "transformer_temperature_avg":   safe_avg(temps),
        "transformer_temperature_max":   safe_max(temps),
        "transformer_voltage_avg":       safe_avg(voltages),
        "transformer_efficiency_avg":    safe_avg(efficiencies),
        "transformer_oil_level_min":     safe_min(oil_levels),
        "transformer_power_factor_avg":  safe_avg(power_factors),
        "transformers_overloaded_count": sum(1 for l in loads if l > 85),
        "transformers_critical_count":   sum(1 for l in loads if l > 95),

        "zone_load_mw_total":       safe_sum(zone_loads_mw),
        "zone_load_percent_avg":    safe_avg(zone_load_pcts),
        "zone_load_percent_max":    safe_max(zone_load_pcts),
        "zone_frequency_avg":       safe_avg(zone_freqs),
        "zone_frequency_min":       safe_min(zone_freqs),
        "zone_voltage_avg":         safe_avg(zone_volts),
        "zone_voltage_min":         safe_min(zone_volts),
        "zone_reactive_power_total":safe_sum(zone_reactive),
        "zones_overloaded_count":   sum(1 for p in zone_load_pcts if p > 85),
        "zones_tripped_count":      sum(
            1 for z in zone_responses if z.get("substation_status") == "tripped"
        ),

        "residual_current_ma_max":   safe_max(residuals) if residuals else 0,
        "current_thd_percent_avg":   safe_avg(thds)      if thds      else 3,
        "insulation_resistance_min": safe_min(insulations) if insulations else 95,
        "arc_signature_score_max":   fault_response.get("arc_signature_score_max", 0),
        "fault_probability_max":     fault_response.get("fault_probability_max", 0),

        "grid_voltage_avg":          vr.get("grid_voltage_avg_v", 230),
        "grid_voltage_min":          vr.get("grid_voltage_min_v", 228),
        "grid_power_factor_avg":     vr.get("grid_power_factor_avg", 0.94),
        "voltage_violations_count":  vr.get("voltage_violations_count", 0),
        "tap_changes_per_hour":      vr.get("tap_changes_per_hour", 0),
        "capacitor_banks_active_count": vr.get("capacitor_banks_active_count", 0),

        "load_delta_mw_total":        total_demand - total_allocated,
        "rebalance_count_session":    lb.get("rebalance_count_session", 0),

        "alert_rate_per_minute":      gc.get("alert_rate_per_minute", 0),
        "remediation_count_session":  gc.get("remediation_count_session", 0),
    }


def extract_features_from_simulated_state(state: dict) -> dict:
    """
    Called at TRAINING TIME by train_model.py.
    State dict must mirror real API response structure.
    """
    return extract_features_from_api_responses(
        transformer_response=state["transformer"],
        zone_responses=state["zones"],
        fault_response=state["fault_detection"],
        voltage_response=state["voltage_regulator"],
        loadbalancer_response=state["load_balancer"],
        gridcontroller_response=state["grid_controller"],
    )


def features_to_vector(feature_dict: dict) -> list:
    """Converts feature dict → ordered list matching FEATURE_COLUMNS."""
    return [feature_dict[col] for col in FEATURE_COLUMNS]


# ─── Safe aggregations ──────────────────────────────────────────────────────────
def safe_avg(lst):
    return sum(lst) / len(lst) if lst else 0

def safe_max(lst):
    return max(lst) if lst else 0

def safe_min(lst):
    return min(lst) if lst else 0

def safe_sum(lst):
    return sum(lst) if lst else 0
