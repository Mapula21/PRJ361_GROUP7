"""
hr_ai.py

Thin integration layer between app.py and the AI/ML heart-rate module
(heart_rate_analyzer.py + ml_anomaly_detector.py, combined by ai_service.py).

Keeping this as its own file means app.py doesn't need to know anything
about how the AI teammate's module works internally - if that module
changes, only this file needs to change.
"""

from ai_service import AIHeartRateService

# One shared instance so the pickled Isolation Forest model is loaded
# from disk only once, not on every request. Age is optional - when not
# provided, the rule-based analyzer falls back to general BPM bands
# instead of age-adjusted zones.
_service_cache: dict[int | None, AIHeartRateService] = {}


def _get_service(age: int | None = None) -> AIHeartRateService:
    if age not in _service_cache:
        _service_cache[age] = AIHeartRateService(age=age)
    return _service_cache[age]


def analyze_reading(bpm: int, age: int | None = None) -> dict:
    """
    Runs both the rule-based analyzer and the pre-trained ML anomaly
    detector on a single reading, and returns a combined result:

        {
            "heart_rate": int,
            "zone": str,             # e.g. "Zone 3 - Moderate"
            "status": str,           # e.g. "Normal" / "Elevated" / "High"
            "anomaly": bool,         # rule-based anomaly flag
            "reason": str,
            "recommendation": str,   # rule-based recommendation text
            "ml_status": str,        # "Normal" / "Anomaly"
            "ml_anomaly": bool,      # ML-based anomaly flag
            "anomaly_score": float,  # Isolation Forest decision score
            "is_anomalous": bool,    # combined flag used to raise an alert
        }
    """
    service = _get_service(age)
    result = service.analyze(bpm)
    result["is_anomalous"] = bool(result["anomaly"] or result["ml_anomaly"])
    return result
