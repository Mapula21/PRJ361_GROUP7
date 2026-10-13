"""
rtdb_models.py

Realtime Database data layer for the AI-Driven Heart Rate Monitoring system.

The Realtime Database is a JSON tree optimised for live/streaming data.
It's ideal for the ESP32 wearable writing raw heart rate readings in
real time, and for the dashboard subscribing to live updates.

Tree structure:
    /athletes/{athlete_id}          - profile + HR baseline
    /athletes/{id}/readings/{ts}    - live readings (nested under athlete)
    /athletes/{id}/alerts/{alertId} - raised alerts
    /athletes/{id}/diagnoses/{id}   - diagnoses

Falls back to SQLite when Firebase (or the Realtime DB) isn't available.
"""

from datetime import datetime, timezone
from firebase_config import get_rtdb, is_firebase_available


def _ref(*paths):
    db = get_rtdb()
    if db is None:
        return None
    ref = db.reference("/")
    for p in paths:
        ref = ref.child(p)
    return ref

def get_athlete(athlete_id) -> dict | None:
    if not is_firebase_available() or not get_rtdb():
        return None
    try:
        val = _ref("athletes", str(athlete_id)).get()
        if val:
            val["id"] = athlete_id
        return val
    except Exception:
        return None


def get_all_athletes() -> list[dict]:
    if not is_firebase_available() or not get_rtdb():
        return []
    try:
        val = _ref("athletes").get()
        if not val:
            return []
        out = []
        if isinstance(val, dict):
            for k, data in val.items():
                if isinstance(data, dict):
                    out.append({**data, "id": str(k)})
        elif isinstance(val, list):
            for i, data in enumerate(val):
                if isinstance(data, dict):
                    out.append({**data, "id": str(i)})
        return out
    except Exception:
        return []


def create_athlete(athlete_id, name, age, resting_hr, max_hr):
    if not is_firebase_available() or not get_rtdb():
        return None
    _ref("athletes", str(athlete_id)).set({
        "name": name,
        "age": age,
        "resting_hr": resting_hr,
        "max_hr": max_hr,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return athlete_id


def seed_demo_athlete_rtdb():
    if not is_firebase_available() or not get_rtdb():
        return
    try:
        existing = _ref("athletes").get()
        if not existing:
            create_athlete(1, "Demo Athlete", 21, 62, 195)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Heart Rate Readings (live stream)
# ---------------------------------------------------------------------------

def push_reading(athlete_id, bpm, zone, timestamp):
    """
    Appends a reading to the athlete's live data node using a push key.
    Returns the generated push key, or None if unavailable.
    """
    if not is_firebase_available() or not get_rtdb():
        return None
    ref = _ref("athletes", str(athlete_id), "readings").push({
        "bpm": bpm,
        "zone": zone,
        "timestamp": timestamp,
    })
    return ref.key


def get_recent_readings(athlete_id, limit=50) -> list[dict]:
    """
    Reads the most recent N readings for an athlete.
    Sorts by timestamp; falls back to a plain fetch if the node lacks an
    .indexOn:'timestamp' rule (avoiding manual rules setup).
    """
    if not is_firebase_available() or not get_rtdb():
        return []
    try:
        query = _ref("athletes", str(athlete_id), "readings").order_by_child("timestamp").limit_to_last(limit)
        val = query.get()
        if not val:
            return []
        raw = val.items()
    except Exception:
        try:
            val = _ref("athletes", str(athlete_id), "readings").get()
            raw = val.items() if val else []
        except Exception:
            return []
    readings = [{**data, "id": key} for key, data in raw]
    readings.sort(key=lambda r: r.get("timestamp", ""))
    return readings[-limit:] if limit else readings


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def raise_alert(athlete_id, reading_id, severity, message, timestamp):
    if not is_firebase_available() or not get_rtdb():
        return None
    ref = _ref("athletes", str(athlete_id), "alerts").push({
        "reading_id": str(reading_id),
        "severity": severity,
        "message": message,
        "acknowledged": False,
        "timestamp": timestamp,
    })
    return ref.key


def update_alert(athlete_id, alert_key, severity, message):
    if not is_firebase_available() or not get_rtdb():
        return
    try:
        _ref("athletes", str(athlete_id), "alerts", alert_key).update({
            "severity": severity,
            "message": message,
        })
    except Exception:
        pass


def get_recent_alerts(athlete_id, limit=20) -> list[dict]:
    if not is_firebase_available() or not get_rtdb():
        return []
    try:
        query = _ref("athletes", str(athlete_id), "alerts").order_by_child("timestamp").limit_to_last(limit)
        val = query.get()
        if not val:
            return []
        raw = val.items()
    except Exception:
        try:
            val = _ref("athletes", str(athlete_id), "alerts").get()
            raw = val.items() if val else []
        except Exception:
            return []
    alerts = [{**data, "id": key} for key, data in raw]
    alerts.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
    return alerts[:limit] if limit else alerts


# ---------------------------------------------------------------------------
# Diagnoses
# ---------------------------------------------------------------------------

def add_diagnosis(athlete_id, alert_id, classification, severity, explanation, timestamp):
    if not is_firebase_available() or not get_rtdb():
        return None
    ref = _ref("athletes", str(athlete_id), "diagnoses").push({
        "alert_id": str(alert_id),
        "classification": classification,
        "severity": severity,
        "explanation": explanation,
        "timestamp": timestamp,
    })
    return ref.key
