"""
analytics.py

Zone classification (Karvonen formula) and anomaly detection.
Matches Milestone 1 section 7.8: Isolation Forest from scikit-learn,
trained per athlete on their own recent readings.

Falls back to a simple threshold check when an athlete doesn't yet
have enough history for the model to train on (cold start).
"""

from sklearn.ensemble import IsolationForest
import numpy as np

MIN_READINGS_FOR_MODEL = 30


def classify_zone(bpm: int, resting_hr: int, max_hr: int) -> int:
    """Karvonen formula: %HRR = (bpm - resting_hr) / (max_hr - resting_hr)."""
    hrr = max_hr - resting_hr
    if hrr <= 0:
        return 1
    pct = (bpm - resting_hr) / hrr

    if pct < 0.5:
        return 1
    elif pct < 0.6:
        return 2
    elif pct < 0.7:
        return 3
    elif pct < 0.85:
        return 4
    else:
        return 5


def is_anomalous(bpm: int, recent_bpms: list[int]) -> bool:
    """
    Returns True if the latest reading looks anomalous relative to the
    athlete's recent history.
    """
    if len(recent_bpms) < MIN_READINGS_FOR_MODEL:
        # Cold start fallback: simple physiological sanity thresholds
        return bpm > 200 or bpm < 35

    X = np.array(recent_bpms).reshape(-1, 1)
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X)
    prediction = model.predict([[bpm]])  # -1 = anomaly, 1 = normal
    return prediction[0] == -1
