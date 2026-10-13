"""
app.py

Flask backend for the AI-Driven Heart Rate Monitoring System.

Per lecturer feedback, this backend now also serves a web-based
dashboard directly (Flask + Jinja2), alongside the existing REST API
that the ESP32 wearable and/or a Flutter app can consume. Nothing
about the underlying architecture changes: still Flask + SQLite +
Isolation Forest, per Milestone 1 section 7.6.

Endpoints:
    POST /heartrate         - ingest a sensor reading
    GET  /analytics         - summary stats for an athlete
    GET  /alerts            - alerts + linked diagnosis for an athlete
    GET  /athlete           - athlete profile + device status
    POST /chat               - chatbot recommendation / Q&A
    GET  /dashboard          - web dashboard (HTML)
"""

from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from models import init_db, seed_demo_athlete, get_db
from hr_ai import analyze_reading
from diagnosis import run_diagnosis
from chatbot import get_recommendation
from firebase_config import init_firebase, is_firebase_available, get_firestore
from auth import require_auth
from insights import (
    LIVE_WINDOW_SECONDS, seconds_since, session_summary, compute_trend, describe_live_state,
)
import firestore_models as fs
import rtdb_models as rtdb

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization", "X-Device-Token"])
init_firebase()

DEVICE_TOKEN = "prj361-esp32-token"  # pre-shared token, per Milestone 1 section 7.9


@app.before_request
def _ensure_db():
    init_db()
    seed_demo_athlete()


@app.route("/health", methods=["GET"])
def health():
    from firebase_config import get_auth
    return jsonify({
        "status": "ok",
        "firebase": {
            "available": is_firebase_available(),
            "firestore": get_firestore() is not None,
            "realtime_db": rtdb.get_rtdb() is not None,
            "auth": get_auth() is not None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Sensor ingestion
# ---------------------------------------------------------------------------

@app.route("/heartrate", methods=["POST"])
@require_auth(allowed_methods=("device_token", "firebase"))
def post_heartrate(auth):
    data = request.get_json(silent=True) or {}

    if request.headers.get("X-Device-Token") != DEVICE_TOKEN:
        return jsonify({"status": "error", "message": "invalid device token"}), 401

    athlete_id = data.get("athlete_id")
    bpm = data.get("bpm")
    if athlete_id is None or bpm is None:
        return jsonify({"status": "error", "message": "athlete_id and bpm are required"}), 400

    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        athlete = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not athlete:
            return jsonify({"status": "error", "message": "unknown athlete_id"}), 404

        ai_result = analyze_reading(bpm, athlete["age"])
        zone = ai_result["zone"]

        cur = conn.execute(
            "INSERT INTO hr_readings (athlete_id, bpm, zone, timestamp) VALUES (?, ?, ?, ?)",
            (athlete_id, bpm, zone, timestamp),
        )
        reading_id = cur.lastrowid

        alert_id = None
        recommendation = None

        if ai_result["is_anomalous"]:
            cur = conn.execute(
                """
                INSERT INTO alerts (athlete_id, reading_id, severity, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (athlete_id, reading_id, "pending", ai_result["reason"], timestamp),
            )
            alert_id = cur.lastrowid

    if is_firebase_available():
        fs.insert_reading(athlete_id, bpm, zone, timestamp)
        rtdb.push_reading(athlete_id, bpm, zone, timestamp)

    # Diagnosis + chatbot recommendation run outside the DB transaction above
    if alert_id:
        diagnosis = run_diagnosis(athlete_id, alert_id, bpm, athlete["resting_hr"])
        try:
            recommendation = get_recommendation(athlete["name"], diagnosis)
        except Exception:
            recommendation = "Recommendation unavailable — could not reach the AI service."

        with get_db() as conn:
            conn.execute(
                "UPDATE alerts SET severity = ?, message = ? WHERE id = ?",
                (diagnosis["severity"], recommendation, alert_id),
            )
        if is_firebase_available():
            fs_alert = fs.insert_alert(athlete_id, str(reading_id), diagnosis["severity"], recommendation, timestamp)
            rtdb_alert = rtdb.raise_alert(athlete_id, reading_id, diagnosis["severity"], recommendation, timestamp)
            fs.insert_diagnosis(str(fs_alert or alert_id), athlete_id, diagnosis["classification"], diagnosis["severity"], diagnosis["explanation"], timestamp)
            rtdb.add_diagnosis(athlete_id, rtdb_alert or str(alert_id), diagnosis["classification"], diagnosis["severity"], diagnosis["explanation"], timestamp)

    return jsonify(
        {
            "status": "success",
            "log_id": reading_id,
            "zone": zone,
            "alert_id": alert_id,
            "recommendation": recommendation,
            "auth_method": auth["method"],
        }
    )


# ---------------------------------------------------------------------------
# Analytics / alerts
# ---------------------------------------------------------------------------

def _live_state(athlete_id: int) -> dict:
    """
    Builds the live picture of an athlete from stored readings: is the device
    streaming, what is the current session, which way is the heart rate moving,
    and what do the rule-based analyzer and ML anomaly model say about the
    latest reading. Shared by /analytics (dashboard) and /chat (assistant).
    """
    with get_db() as conn:
        athlete = conn.execute(
            "SELECT id, name, age, resting_hr, max_hr FROM athletes WHERE id = ?",
            (athlete_id,),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT bpm, zone, timestamp
            FROM hr_readings
            WHERE athlete_id = ?
            ORDER BY id DESC
            LIMIT 3000
            """,
            (athlete_id,),
        ).fetchall()

    readings = [dict(r) for r in reversed(rows)]  # oldest -> newest
    state = {
        "athlete": dict(athlete) if athlete else None,
        "readings": readings,
        "latest": readings[-1] if readings else None,
        "session": None,
        "trend": {"direction": "unknown", "change_bpm": None},
        "seconds_since": None,
        "is_live": False,
        "ai": None,
    }
    if not readings:
        return state

    state["seconds_since"] = seconds_since(state["latest"]["timestamp"])
    state["is_live"] = (
        state["seconds_since"] is not None and state["seconds_since"] <= LIVE_WINDOW_SECONDS
    )

    session, session_bpms = session_summary(readings)
    state["session"] = session

    if state["is_live"]:
        state["trend"] = compute_trend(session_bpms)
        try:
            result = analyze_reading(int(state["latest"]["bpm"]), athlete["age"] if athlete else None)
            state["ai"] = {
                key: result.get(key)
                for key in (
                    "zone", "status", "reason", "recommendation",
                    "ml_status", "ml_anomaly", "anomaly_score", "is_anomalous",
                )
            }
        except Exception:
            state["ai"] = None  # never let an AI hiccup break the dashboard

    return state


@app.route("/analytics", methods=["GET"])
@require_auth(allowed_methods=("firebase", "device_token"))
def get_analytics(auth):
    athlete_id = request.args.get("athlete_id", type=int)
    if not athlete_id:
        return jsonify({"status": "error", "message": "athlete_id is required"}), 400

    state = _live_state(athlete_id)

    # Existing summary keys: based on the most recent 100 readings (oldest -> newest).
    recent_readings = state["readings"][-100:]
    bpms = [r["bpm"] for r in recent_readings]

    payload = {
        "status": "success",
        "current_bpm": None,
        "current_zone": None,
        "average_bpm": None,
        "peak_bpm": None,
        "sample_size": 0,
        "recent_readings": [],
        # Live context used by the dashboard
        "is_live": state["is_live"],
        "seconds_since_last_reading": state["seconds_since"],
        "trend": state["trend"],
        "session": state["session"],
        "ai": state["ai"],
    }

    if bpms:
        latest = recent_readings[-1]
        payload.update({
            "current_bpm": latest["bpm"],
            "current_zone": latest["zone"],
            "average_bpm": round(sum(bpms) / len(bpms), 1),
            "peak_bpm": max(bpms),
            "sample_size": len(bpms),
            "recent_readings": recent_readings[-30:],
        })

    return jsonify(payload)


@app.route("/athlete", methods=["GET"])
@require_auth(allowed_methods=("firebase", "device_token"))
def get_athlete(auth):
    """Athlete profile used by the dashboard, plus whether the device is streaming."""
    athlete_id = request.args.get("athlete_id", type=int)
    if not athlete_id:
        return jsonify({"status": "error", "message": "athlete_id is required"}), 400

    with get_db() as conn:
        athlete = conn.execute(
            "SELECT id, name, age, resting_hr, max_hr FROM athletes WHERE id = ?",
            (athlete_id,),
        ).fetchone()
        last = conn.execute(
            "SELECT timestamp FROM hr_readings WHERE athlete_id = ? ORDER BY id DESC LIMIT 1",
            (athlete_id,),
        ).fetchone()

    if not athlete:
        return jsonify({"status": "error", "message": "unknown athlete_id"}), 404

    age = athlete["age"]
    last_seen = seconds_since(last["timestamp"]) if last else None

    return jsonify({
        "status": "success",
        "athlete": {
            "id": athlete["id"],
            "name": athlete["name"],
            "age": age,
            "resting_hr": athlete["resting_hr"],
            # The zone analyzer estimates max heart rate as 220 minus age.
            "estimated_max_hr": (220 - age) if age else None,
        },
        "device": {
            "name": "PRJ361-ESP32",
            "last_seen_seconds": last_seen,
            "online": last_seen is not None and last_seen <= LIVE_WINDOW_SECONDS,
        },
    })


@app.route("/history", methods=["GET"])
@require_auth(allowed_methods=("firebase", "device_token"))
def get_history(auth):
    """Return daily monitoring summaries built from stored heart-rate readings.

    The prototype database does not have a separate sessions table, so the
    frontend uses each calendar day with readings as a monitoring session.
    Duration is calculated from the first to the last reading when there is
    more than one reading. Recovery is not fabricated because the backend
    does not currently store a recovery metric.
    """
    athlete_id = request.args.get("athlete_id", type=int)
    if not athlete_id:
        return jsonify({"status": "error", "message": "athlete_id is required"}), 400

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, bpm, zone, timestamp
            FROM hr_readings
            WHERE athlete_id = ?
            ORDER BY id DESC
            LIMIT 500
            """,
            (athlete_id,),
        ).fetchall()
        alert_rows = conn.execute(
            """
            SELECT timestamp
            FROM alerts
            WHERE athlete_id = ?
            ORDER BY id DESC
            LIMIT 500
            """,
            (athlete_id,),
        ).fetchall()

    from collections import defaultdict
    groups = defaultdict(list)
    for row in rows:
        item = dict(row)
        day = str(item["timestamp"])[:10]
        groups[day].append(item)

    alert_days = {str(row["timestamp"])[:10] for row in alert_rows}
    sessions = []

    for day, items in sorted(groups.items(), reverse=True):
        bpms = [int(item["bpm"]) for item in items]
        times = []
        for item in items:
            try:
                value = str(item["timestamp"]).replace("Z", "+00:00")
                times.append(datetime.fromisoformat(value))
            except (TypeError, ValueError):
                pass

        duration_minutes = None
        if len(times) >= 2:
            duration_minutes = max(0, round((max(times) - min(times)).total_seconds() / 60))

        sessions.append({
            "date": day,
            "session": "Monitoring",
            "reading_count": len(bpms),
            "average_bpm": round(sum(bpms) / len(bpms), 1),
            "peak_bpm": max(bpms),
            "duration_minutes": duration_minutes,
            "status": "Alert" if day in alert_days else "Normal",
        })

    return jsonify({"status": "success", "sessions": sessions[:30]})


@app.route("/alerts", methods=["GET"])
@require_auth(allowed_methods=("firebase", "device_token"))
def get_alerts(auth):
    athlete_id = request.args.get("athlete_id", type=int)
    if not athlete_id:
        return jsonify({"status": "error", "message": "athlete_id is required"}), 400

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.severity, a.message, a.timestamp,
                   d.classification, d.explanation
            FROM alerts a
            LEFT JOIN diagnoses d ON d.alert_id = a.id
            WHERE a.athlete_id = ?
            ORDER BY a.id DESC LIMIT 20
            """,
            (athlete_id,),
        ).fetchall()

    return jsonify({"status": "success", "alerts": [dict(r) for r in rows]})


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------

@app.route("/chat", methods=["POST"])
@require_auth(allowed_methods=("firebase", "device_token"))
def post_chat(auth):
    data = request.get_json(silent=True) or {}
    athlete_id = data.get("athlete_id")
    message = data.get("message")

    if not athlete_id or not message:
        return jsonify({"status": "error", "message": "athlete_id and message are required"}), 400

    with get_db() as conn:
        athlete = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not athlete:
            return jsonify({"status": "error", "message": "unknown athlete_id"}), 404

        latest_diag = conn.execute(
            "SELECT * FROM diagnoses WHERE athlete_id = ? ORDER BY id DESC LIMIT 1",
            (athlete_id,),
        ).fetchone()

    diagnosis = None
    if latest_diag:
        diagnosis = {
            "classification": latest_diag["classification"],
            "severity": latest_diag["severity"],
            "explanation": latest_diag["explanation"],
            "recent_bpms": [],
        }

    # Ground the assistant in what the sensor is reporting right now.
    live_context = ""
    try:
        state = _live_state(athlete_id)
        if state["is_live"] and state["latest"]:
            live_context = "Live data: " + describe_live_state(
                state["latest"]["bpm"], state["ai"], state["trend"], state["session"]
            ) + "\n\n"
        elif state["latest"]:
            live_context = (
                "No live reading right now; the device last reported "
                f"{state['seconds_since']} seconds ago.\n\n"
            )
    except Exception:
        live_context = ""

    try:
        reply = get_recommendation(
            athlete["name"], diagnosis, user_message=f"{live_context}Athlete's question: {message}"
        )
    except Exception:
        reply = "Sorry, I couldn't reach the AI service right now. Please try again shortly."

    return jsonify({"status": "success", "reply": reply})


# ---------------------------------------------------------------------------
# Web dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard", methods=["GET"])
def dashboard():
    athlete_id = request.args.get("athlete_id", 1, type=int)

    with get_db() as conn:
        athlete = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        readings = conn.execute(
            "SELECT bpm, zone, timestamp FROM hr_readings WHERE athlete_id = ? ORDER BY id DESC LIMIT 30",
            (athlete_id,),
        ).fetchall()
        alerts = conn.execute(
            """
            SELECT a.severity, a.message, a.timestamp, d.classification, d.explanation
            FROM alerts a LEFT JOIN diagnoses d ON d.alert_id = a.id
            WHERE a.athlete_id = ? ORDER BY a.id DESC LIMIT 10
            """,
            (athlete_id,),
        ).fetchall()

    readings_list = [dict(r) for r in reversed(readings)]  # oldest -> newest for chart
    bpms = [r["bpm"] for r in readings_list]

    summary = {
        "current_bpm": bpms[-1] if bpms else None,
        "current_zone": readings_list[-1]["zone"] if readings_list else None,
        "average_bpm": round(sum(bpms) / len(bpms), 1) if bpms else None,
        "peak_bpm": max(bpms) if bpms else None,
    }

    return render_template(
        "dashboard.html",
        athlete=athlete,
        readings=readings_list,
        alerts=[dict(a) for a in alerts],
        summary=summary,
    )


if __name__ == "__main__":
    init_db()
    seed_demo_athlete()
    app.run(host="0.0.0.0", port=5000, debug=True)
