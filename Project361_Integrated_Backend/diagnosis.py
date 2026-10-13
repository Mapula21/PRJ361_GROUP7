"""
diagnosis.py

Runs a short diagnosis pass whenever an alert is raised — not on every
reading, only at alert time, to keep it lightweight (per Milestone 1
scope: rule-based logic + basic ML, not a full clinical diagnostic tool).

It looks at the athlete's recent reading window and classifies what
kind of abnormal pattern occurred, so the alert carries useful context
instead of just "reading flagged as anomalous."
"""

from datetime import datetime, timezone
from models import get_db

WINDOW_SIZE = 10  # number of recent readings considered


def _fetch_recent_readings(conn, athlete_id: int, limit: int = WINDOW_SIZE):
    rows = conn.execute(
        """
        SELECT bpm, timestamp FROM hr_readings
        WHERE athlete_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (athlete_id, limit),
    ).fetchall()
    return [r["bpm"] for r in reversed(rows)]  # oldest -> newest


def classify_pattern(bpm: int, recent_bpms: list[int], resting_hr: int) -> tuple[str, str]:
    """
    Returns (classification, severity) based on simple, explainable rules.
    """
    if not recent_bpms:
        return "insufficient_data", "low"

    avg_recent = sum(recent_bpms) / len(recent_bpms)
    jump = bpm - recent_bpms[-2] if len(recent_bpms) >= 2 else 0

    if bpm < resting_hr - 15:
        return "abnormally_low", "high"
    if jump > 40:
        return "sudden_spike", "high"
    if bpm > avg_recent + 25:
        return "sustained_elevation", "medium"
    if max(recent_bpms) - min(recent_bpms) > 50:
        return "irregular_pattern", "medium"

    return "flagged_reading", "low"


CLASSIFICATION_EXPLANATIONS = {
    "sudden_spike": "Heart rate jumped sharply compared to the previous reading.",
    "sustained_elevation": "Heart rate has stayed well above the athlete's recent average.",
    "irregular_pattern": "Readings over the recent window are fluctuating unusually widely.",
    "abnormally_low": "Heart rate has dropped notably below the athlete's resting baseline.",
    "flagged_reading": "Reading was statistically unusual but doesn't match a specific pattern.",
    "insufficient_data": "Not enough recent readings to characterise the anomaly.",
}


def run_diagnosis(athlete_id: int, alert_id: int, bpm: int, resting_hr: int) -> dict:
    """
    Runs the diagnosis and stores it in the diagnoses table.
    Returns the diagnosis dict so it can be reused by the chatbot / API response.
    """
    with get_db() as conn:
        recent = _fetch_recent_readings(conn, athlete_id)
        classification, severity = classify_pattern(bpm, recent, resting_hr)
        explanation = CLASSIFICATION_EXPLANATIONS[classification]
        timestamp = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO diagnoses (alert_id, athlete_id, classification, severity, explanation, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (alert_id, athlete_id, classification, severity, explanation, timestamp),
        )

    return {
        "alert_id": alert_id,
        "athlete_id": athlete_id,
        "classification": classification,
        "severity": severity,
        "explanation": explanation,
        "recent_bpms": recent,
    }
