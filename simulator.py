"""Deterministic, offline sensor simulator for MachineSense."""
from __future__ import annotations
import numpy as np
import pandas as pd

SENSORS = ["vibration", "temperature", "current", "dust"]
MACHINES = {
    "Powerloom 1": {"vibration": 2.0, "temperature": 62.0, "current": 8.0, "dust": 24.0, "location": "Coimbatore"},
    "Flour Mill 1": {"vibration": 1.2, "temperature": 55.0, "current": 12.0, "dust": 32.0, "location": "Erode"},
    "Pump Set 1": {"vibration": 0.8, "temperature": 48.0, "current": 5.0, "dust": 18.0, "location": "Tiruppur"},
}

def generate_history(machine: str, days: int = 30, seed: int = 13) -> pd.DataFrame:
    """Create baseline readings for model training and initial chart history."""
    rng = np.random.default_rng(seed + list(MACHINES).index(machine))
    base = MACHINES[machine]
    idx = pd.date_range(end=pd.Timestamp.now().normalize(), periods=days, freq="D")
    return pd.DataFrame({
        "date": idx,
        "vibration": rng.normal(base["vibration"], base["vibration"] * .07, days).clip(0),
        "temperature": rng.normal(base["temperature"], 1.8, days),
        "current": rng.normal(base["current"], base["current"] * .06, days).clip(0),
        "dust": rng.normal(base["dust"], 3.5, days).clip(0),
        "fault": False, "dust_injected": False,
    })

def next_reading(machine: str, history: pd.DataFrame, fault_days: int = 0, dusty: bool = False) -> dict:
    base = MACHINES[machine]
    day = len(history)
    rng = np.random.default_rng(900 + day * 7 + list(MACHINES).index(machine))
    drift = min(fault_days, 12) / 12
    dust = max(0, rng.normal(base["dust"] + (70 if dusty else 0), 3.2))
    return {"date": pd.Timestamp.now().normalize() + pd.Timedelta(days=max(0, day-30)),
            "vibration": max(.01, rng.normal(base["vibration"] * (1 + .75*drift), base["vibration"]*.045)),
            "temperature": rng.normal(base["temperature"] + 13*drift + (5 if dusty else 0), 1.0),
            "current": max(.01, rng.normal(base["current"] * (1 + .12*drift), base["current"]*.04)),
            "dust": dust, "fault": fault_days > 0, "dust_injected": dusty}
