"""Fact-grounded alert stories and repair planning."""
def make_story(machine: str, result: dict, row: dict, repair_log) -> str:
    if result["status"] == "Normal":
        return f"{machine} readings are within its learned normal range. Continue monitoring."
    sensor = result["sensor"]
    pct = max(0, result["deviation_pct"])
    if sensor == "vibration" and result["deviations"].get("temperature", 0) > 5:
        likely = "The pattern is consistent with possible bearing wear."
    elif sensor == "dust":
        likely = "Dust is elevated; it is a risk factor. Clean the vents and recheck temperature."
    else:
        likely = f"{sensor.title()} is the largest deviation; the cause is not yet established."
    story = (f"{machine} {sensor} is {pct:.0f}% above its own normal. "
             f"Anomaly score: {result['anomaly_score']:.2f}. {likely} "
             f"Confidence: {result['confidence']}. Suggested repair window: Sunday, 2 pm–6 pm (configurable).")
    try:
        similar = repair_log[(repair_log.machine == machine) & (repair_log.part.str.contains("bearing", case=False, na=False))]
        if not similar.empty:
            story += " A similar logged issue was repaired by replacing the bearing."
    except (AttributeError, KeyError):
        pass
    return story
