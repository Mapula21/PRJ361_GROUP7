from heart_rate_analyzer import HeartRateAnalyzer
from ml_anomaly_detector import MLHeartRateDetector


class AIHeartRateService:

    def __init__(self, age=None):
        self.rule_analyzer = HeartRateAnalyzer(age)
        self.ml_detector = MLHeartRateDetector()

    def analyze(self, heart_rate):
        # Rule-based heart-rate analysis
        rule_result = self.rule_analyzer.analyze(heart_rate)

        # Machine Learning anomaly detection
        ml_result = self.ml_detector.predict(heart_rate)

        # Combine both results
        return {
            "heart_rate": heart_rate,

            "zone": rule_result.zone,
            "status": rule_result.status,
            "anomaly": rule_result.anomaly,
            "reason": rule_result.reason,
            "recommendation": rule_result.recommendation,

            "ml_status": ml_result["ml_status"],
            "ml_anomaly": ml_result["ml_anomaly"],
            "anomaly_score": ml_result["anomaly_score"]
        }


if __name__ == "__main__":

    service = AIHeartRateService(age=20)

    test_readings = [70, 100, 120, 150, 180, 220, 250]

    print()
    print("AI HEART RATE ANALYSIS")
    print("=" * 50)

    for reading in test_readings:

        result = service.analyze(reading)

        print()
        print("Heart Rate:", result["heart_rate"], "BPM")
        print("Zone:", result["zone"])
        print("Status:", result["status"])
        print("Rule Anomaly:", result["anomaly"])
        print("ML Status:", result["ml_status"])
        print("ML Anomaly:", result["ml_anomaly"])
        print("Anomaly Score:", result["anomaly_score"])
        print("Recommendation:", result["recommendation"])