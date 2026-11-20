"""Per-machine unsupervised anomaly scoring."""
from __future__ import annotations
from sklearn.ensemble import IsolationForest
import numpy as np
import pandas as pd
from simulator import SENSORS

def train_models(histories: dict[str, pd.DataFrame], n_normal: int = 25) -> dict:
    models = {}
    for machine, frame in histories.items():
        normal = frame.loc[~frame.get("fault", False), SENSORS].head(n_normal)
        clf = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
        clf.fit(normal)
        models[machine] = {"model": clf, "baseline": normal.mean(), "scale": normal.std().replace(0, 1)}
    return models

def score_reading(machine: str, row: dict, models: dict, threshold_bias: float = 0.0) -> dict:
    item = models[machine]
    x = pd.DataFrame([[row[s] for s in SENSORS]], columns=SENSORS)
    raw = float(item["model"].decision_function(x)[0])
    anomaly_score = float(np.clip(0.5 - raw * 3.0, 0, 1))
    ratios = {s: (float(row[s]) / max(float(item["baseline"][s]), 1e-6) - 1) * 100 for s in SENSORS}
    # Isolation Forest score and transparent baseline deviation jointly determine the status.
    max_deviation = max(ratios.values())
    alert_limit = float(np.clip(.78 + threshold_bias, .62, .9))
    watch_limit = float(np.clip(.58 + threshold_bias, .45, .78))
    if anomaly_score >= alert_limit or max_deviation >= 45 + threshold_bias * 100:
        status = "Alert"
    elif anomaly_score >= watch_limit or max_deviation >= 20 + threshold_bias * 50:
        status = "Watch"
    else:
        status = "Normal"
    sensor = max(ratios, key=ratios.get)
    confidence = "high" if status == "Alert" and (anomaly_score > .88 or max_deviation > 70) else "medium" if status != "Normal" else "low"
    return {"status": status, "anomaly_score": anomaly_score, "deviations": ratios,
            "sensor": sensor, "deviation_pct": ratios[sensor], "confidence": confidence}
