"""
insights.py

Small, dependency-free helpers that turn raw heart-rate readings into the
live context the dashboard and the chatbot use:

- is the device currently streaming?
- what is the current session (a run of readings with no long gaps)?
- is the heart rate rising, falling or steady?

Nothing in here is a medical measurement. It only summarises the readings
the sensor has sent.
"""

from datetime import datetime, timezone

LIVE_WINDOW_SECONDS = 15      # a reading newer than this counts as "live"
SESSION_GAP_SECONDS = 300     # a gap longer than this starts a new session
TREND_WINDOW = 6              # readings per window when judging the trend
TREND_THRESHOLD_BPM = 4.0     # minimum change in average BPM to call it rising/falling


def parse_ts(value):
    """Parse an ISO timestamp into an aware UTC datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def seconds_since(value, now=None):
    """Whole seconds between a timestamp and now (never negative), or None."""
    dt = parse_ts(value)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, int((now - dt).total_seconds()))


def session_summary(readings, gap_seconds=SESSION_GAP_SECONDS):
    """
    readings: list of dicts with 'bpm' and 'timestamp', oldest -> newest.
    Returns (summary, bpms) for the newest unbroken run of readings,
    or (None, []) when there is nothing usable.
    """
    points = []
    for r in readings:
        t = parse_ts(r.get("timestamp"))
        try:
            b = int(r.get("bpm"))
        except (TypeError, ValueError):
            continue
        if t is not None:
            points.append((t, b))

    if not points:
        return None, []

    start = len(points) - 1
    while start > 0 and abs((points[start][0] - points[start - 1][0]).total_seconds()) <= gap_seconds:
        start -= 1

    segment = points[start:]
    bpms = [b for _, b in segment]
    duration = max(0, int((segment[-1][0] - segment[0][0]).total_seconds()))

    summary = {
        "start": segment[0][0].isoformat(),
        "duration_seconds": duration,
        "reading_count": len(bpms),
        "average_bpm": round(sum(bpms) / len(bpms), 1),
        "peak_bpm": max(bpms),
        "min_bpm": min(bpms),
    }
    return summary, bpms


def compute_trend(bpms, window=TREND_WINDOW, threshold=TREND_THRESHOLD_BPM):
    """Compare the average of the latest `window` readings with the `window` before them."""
    if len(bpms) < 2 * window:
        return {"direction": "unknown", "change_bpm": None}

    recent = sum(bpms[-window:]) / window
    previous = sum(bpms[-2 * window:-window]) / window
    change = round(recent - previous, 1)

    if change >= threshold:
        direction = "rising"
    elif change <= -threshold:
        direction = "falling"
    else:
        direction = "steady"
    return {"direction": direction, "change_bpm": change}


def describe_live_state(bpm, ai, trend, session):
    """One short paragraph of live context for the chatbot prompt."""
    parts = [f"Current reading: {bpm} BPM."]
    if ai:
        parts.append(
            f"Zone: {ai.get('zone')}. Rule-based status: {ai.get('status')}. "
            f"ML anomaly check: {ai.get('ml_status')}."
        )
    if trend and trend.get("direction") != "unknown":
        parts.append(
            f"Trend: {trend['direction']} ({trend['change_bpm']:+} BPM versus the previous readings)."
        )
    if session:
        minutes = round(session["duration_seconds"] / 60, 1)
        parts.append(
            f"Current session: {session['reading_count']} readings over {minutes} minutes, "
            f"average {session['average_bpm']} BPM, peak {session['peak_bpm']} BPM."
        )
    return " ".join(parts)
