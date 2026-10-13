"""
AI Heart Rate Analyzer
Heart Rate Monitor for Athletics

Role: AI and Machine Learning Researcher
Team member: Xolile Luyanda Madonsela

This prototype analyses heart-rate readings and:
- determines an exercise heart-rate zone
- identifies elevated or unusual readings
- flags potential anomalies
- provides a monitoring recommendation

This is an academic prototype and NOT a medical diagnostic system.
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class HeartRateAnalysis:
    heart_rate: int
    age: Optional[int]
    max_heart_rate: Optional[int]
    zone: str
    status: str
    anomaly: bool
    reason: str
    recommendation: str

    def to_dict(self):
        """Convert the analysis result into a dictionary."""
        return asdict(self)


class HeartRateAnalyzer:

    def __init__(self, age=None):
        if age is not None and not 10 <= age <= 100:
            raise ValueError("Age must be between 10 and 100.")

        self.age = age

        if age is not None:
            self.max_heart_rate = 220 - age
        else:
            self.max_heart_rate = None

    def validate_heart_rate(self, heart_rate):
        """Check that the heart-rate value is valid."""

        if not isinstance(heart_rate, (int, float)):
            raise TypeError("Heart rate must be a number.")

        if heart_rate <= 0 or heart_rate > 300:
            raise ValueError(
                "Heart rate must be between 1 and 300 BPM."
            )

    def get_zone(self, heart_rate):
        """Determine the athlete's heart-rate exercise zone."""

        # If age is not provided, use general BPM categories
        if self.max_heart_rate is None:

            if heart_rate < 60:
                return "Below Normal"

            elif heart_rate < 100:
                return "Low"

            elif heart_rate < 140:
                return "Moderate"

            elif heart_rate < 170:
                return "High"

            else:
                return "Very High"

        # Calculate percentage of estimated maximum heart rate
        percentage = heart_rate / self.max_heart_rate

        if percentage < 0.50:
            return "Below Zone 1"

        elif percentage < 0.60:
            return "Zone 1 - Very Light"

        elif percentage < 0.70:
            return "Zone 2 - Light"

        elif percentage < 0.80:
            return "Zone 3 - Moderate"

        elif percentage < 0.90:
            return "Zone 4 - Hard"

        elif percentage <= 1.00:
            return "Zone 5 - Maximum"

        else:
            return "Above Estimated Maximum"

    def analyze(self, heart_rate):
        """Analyse a single heart-rate reading."""

        self.validate_heart_rate(heart_rate)

        zone = self.get_zone(heart_rate)

        anomaly = False

        status = "Normal"

        reason = (
            "Heart rate is within the expected monitoring range."
        )

        recommendation = (
            "Continue monitoring heart rate and exercise intensity."
        )

        # Unusually low heart rate
        if heart_rate < 40:

            anomaly = True

            status = "Abnormally Low"

            reason = (
                "The reading is unusually low for an exercising athlete."
            )

            recommendation = (
                "Reduce or stop exercise and monitor the reading. "
                "If the athlete feels unwell, seek appropriate medical help."
            )

        # Above estimated maximum heart rate
        elif (
            self.max_heart_rate is not None
            and heart_rate > self.max_heart_rate
        ):

            anomaly = True

            status = "Above Estimated Maximum"

            reason = (
                "The reading is above the athlete's estimated "
                "maximum heart rate."
            )

            recommendation = (
                "Reduce exercise intensity and recheck the reading. "
                "If symptoms occur, seek appropriate medical assistance."
            )

        # Very high heart rate when age is unavailable
        elif self.max_heart_rate is None and heart_rate >= 190:

            anomaly = True

            status = "Very High"

            reason = (
                "The reading is very high and should be monitored carefully."
            )

            recommendation = (
                "Reduce exercise intensity and recheck the reading. "
                "If symptoms occur, seek appropriate medical assistance."
            )

        # Maximum exercise zone
        elif zone in ["Zone 5 - Maximum", "Very High"]:

            status = "High"

            reason = (
                "Heart rate is in a very high exercise-intensity range."
            )

            recommendation = (
                "Monitor closely and consider reducing intensity if the "
                "athlete is not intentionally performing maximum-effort exercise."
            )

        # Hard exercise zone
        elif zone in ["Zone 4 - Hard", "High"]:

            status = "Elevated"

            reason = (
                "Heart rate indicates high exercise intensity."
            )

            recommendation = (
                "Monitor the athlete and allow recovery when appropriate."
            )

        return HeartRateAnalysis(
            heart_rate=int(heart_rate),
            age=self.age,
            max_heart_rate=self.max_heart_rate,
            zone=zone,
            status=status,
            anomaly=anomaly,
            reason=reason,
            recommendation=recommendation
        )


def analyze_heart_rate(heart_rate, age=None):
    """
    Convenience function for Flask/backend integration.

    Returns a dictionary that can easily be converted to JSON.
    """

    analyzer = HeartRateAnalyzer(age)

    result = analyzer.analyze(heart_rate)

    return result.to_dict()


# Demonstration
if __name__ == "__main__":

    print("AI HEART RATE ANALYZER")
    print("=" * 30)

    analyzer = HeartRateAnalyzer(age=20)

    test_readings = [45, 90, 120, 150, 175, 195, 210]

    for reading in test_readings:

        result = analyzer.analyze(reading)

        print()
        print("Heart Rate:", result.heart_rate, "BPM")
        print("Zone:", result.zone)
        print("Status:", result.status)
        print("Anomaly:", result.anomaly)
        print("Reason:", result.reason)
        print("Recommendation:", result.recommendation)