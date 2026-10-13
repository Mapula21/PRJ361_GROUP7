"""
Machine Learning Heart Rate Anomaly Detector

Uses an Isolation Forest model to identify unusual
heart-rate readings.
"""

import joblib
from pathlib import Path

DEFAULT_MODEL_PATH = Path(__file__).parent / "heart_rate_model.pkl"


class MLHeartRateDetector:

    def __init__(self, model_path=DEFAULT_MODEL_PATH):

        self.model = joblib.load(model_path)

    def predict(self, heart_rate):

        if not isinstance(heart_rate, (int, float)):
            raise TypeError(
                "Heart rate must be a number."
            )

        if heart_rate <= 0 or heart_rate > 300:
            raise ValueError(
                "Heart rate must be between 1 and 300 BPM."
            )

        # The model expects a two-dimensional input
        data = [[heart_rate]]

        prediction = self.model.predict(data)[0]

        score = self.model.decision_function(data)[0]

        if prediction == -1:

            status = "Anomaly"
            anomaly = True

        else:

            status = "Normal"
            anomaly = False

        return {
            "heart_rate": heart_rate,
            "ml_status": status,
            "ml_anomaly": anomaly,
            "anomaly_score": round(float(score), 4)
        }


if __name__ == "__main__":

    detector = MLHeartRateDetector()

    test_readings = [
        80,
        120,
        150,
        175,
        220,
        250
    ]

    print("ML HEART RATE ANOMALY DETECTOR")
    print("=" * 40)

    for reading in test_readings:

        result = detector.predict(reading)

        print()
        print("Heart Rate:", result["heart_rate"], "BPM")
        print("ML Status:", result["ml_status"])
        print("ML Anomaly:", result["ml_anomaly"])
        print("Anomaly Score:", result["anomaly_score"])