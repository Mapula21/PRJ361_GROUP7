"""
firestore_models.py

Firestore data layer for the AI-Driven Heart Rate Monitoring backend.
Provides the same interface as models.py but stores data in Google
Cloud Firestore instead of local SQLite.

Collections:
    athletes        - athlete profile + HR baseline (resting/max)
    hr_readings      - one row per incoming sensor reading
    alerts          - raised when a reading is flagged anomalous
    diagnoses       - detailed diagnosis generated when an alert fires

Falls back to SQLite (models.py) when Firebase is not configured.
"""

from datetime import datetime, timezone
from firebase_config import get_firestore, is_firebase_available


def _col(name):
    """Returns a Firestore collection reference."""
    return get_firestore().collection(name)


# ---------------------------------------------------------------------------
# Athletes
# ---------------------------------------------------------------------------

def get_athlete(athlete_id: int) -> dict | None:
    if not is_firebase_available():
        return None
    doc = _col("athletes").document(str(athlete_id)).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = int(doc.id)
        return data
    return None


def get_all_athletes() -> list[dict]:
    if not is_firebase_available():
        return []
    return [
        {**doc.to_dict(), "id": int(doc.id)}
        for doc in _col("athletes").stream()
    ]


def create_athlete(name: str, age: int, resting_hr: int, max_hr: int) -> str:
    if not is_firebase_available():
        return None
    ref = _col("athletes").document()
    ref.set({
        "name": name,
        "age": age,
        "resting_hr": resting_hr,
        "max_hr": max_hr,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return ref.id


def seed_demo_athlete_firestore():
    """Creates one demo athlete if the collection is empty."""
    if not is_firebase_available():
        return
    existing = _col("athletes").limit(1).stream()
    if not any(True for _ in existing):
        create_athlete("Athlete", 21, 62, 195)


# ---------------------------------------------------------------------------
# Heart Rate Readings
# ---------------------------------------------------------------------------

def insert_reading(athlete_id: int, bpm: int, zone: int, timestamp: str) -> str:
    if not is_firebase_available():
        return None
    ref = _col("hr_readings").document()
    ref.set({
        "athlete_id": athlete_id,
        "bpm": bpm,
        "zone": zone,
        "timestamp": timestamp,
    })
    return ref.id


def _stream_fallback(query, col_name, athlete_id, limit):
    """
    Tries a compound Firestore query; on index errors, falls back to a
    simple fetch + in-memory sort/filter so the app works without
    manually creating composite Firestore indexes.
    """
    try:
        return [doc.to_dict() | {"id": doc.id} for doc in query.stream()]
    except Exception:
        rows = [doc.to_dict() | {"id": doc.id} for doc in _col(col_name).stream()]
        filtered = [r for r in rows if r.get("athlete_id") == athlete_id]
        filtered.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return filtered[:limit]


def get_recent_readings(athlete_id: int, limit: int = 50) -> list[dict]:
    if not is_firebase_available():
        return []
    query = (
        _col("hr_readings")
        .where("athlete_id", "==", athlete_id)
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
    )
    return _stream_fallback(query, "hr_readings", athlete_id, limit)


def get_all_readings(athlete_id: int, limit: int = 100) -> list[dict]:
    if not is_firebase_available():
        return []
    query = (
        _col("hr_readings")
        .where("athlete_id", "==", athlete_id)
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
    )
    return _stream_fallback(query, "hr_readings", athlete_id, limit)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def insert_alert(athlete_id: int, reading_id: str, severity: str, message: str, timestamp: str) -> str:
    if not is_firebase_available():
        return None
    ref = _col("alerts").document()
    ref.set({
        "athlete_id": athlete_id,
        "reading_id": reading_id,
        "severity": severity,
        "message": message,
        "acknowledged": False,
        "timestamp": timestamp,
    })
    return ref.id


def update_alert(alert_id: str, severity: str, message: str):
    if not is_firebase_available():
        return
    _col("alerts").document(alert_id).update({
        "severity": severity,
        "message": message,
    })


def get_recent_alerts(athlete_id: int, limit: int = 20) -> list[dict]:
    if not is_firebase_available():
        return []
    query = (
        _col("alerts")
        .where("athlete_id", "==", athlete_id)
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
    )
    return _stream_fallback(query, "alerts", athlete_id, limit)


# ---------------------------------------------------------------------------
# Diagnoses
# ---------------------------------------------------------------------------

def insert_diagnosis(
    alert_id: str,
    athlete_id: int,
    classification: str,
    severity: str,
    explanation: str,
    timestamp: str,
) -> str:
    if not is_firebase_available():
        return None
    ref = _col("diagnoses").document()
    ref.set({
        "alert_id": alert_id,
        "athlete_id": athlete_id,
        "classification": classification,
        "severity": severity,
        "explanation": explanation,
        "timestamp": timestamp,
    })
    return ref.id


def get_latest_diagnosis(athlete_id: int) -> dict | None:
    if not is_firebase_available():
        return None
    query = (
        _col("diagnoses")
        .where("athlete_id", "==", athlete_id)
        .order_by("timestamp", direction="DESCENDING")
        .limit(1)
    )
    try:
        snapshots = list(query.stream())
        docs = [{**s.to_dict(), "id": s.id} for s in snapshots]
    except Exception:
        docs = _stream_fallback(query, "diagnoses", athlete_id, 1)
    if docs:
        return docs[0]
    return None


def get_diagnosis_for_alert(alert_id: str) -> dict | None:
    if not is_firebase_available():
        return None
    query = _col("diagnoses").where("alert_id", "==", alert_id).limit(1)
    docs = list(query.stream())
    if docs:
        data = docs[0].to_dict()
        data["id"] = docs[0].id
        return data
    return None
