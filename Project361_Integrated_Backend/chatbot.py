"""
chatbot.py

Recommendation chatbot. Uses the existing Google Gemini API rather
than a custom-built model, per project decision — the value here is
grounding the chatbot's answers in the athlete's real diagnosis/reading
data, not building an LLM from scratch. Gemini's free tier (via Google
AI Studio) requires no credit card, which is why it's used here instead
of a paid API.

Requires the GEMINI_API_KEY environment variable to be set on the
deployment (Render.com env vars, per Milestone 1 deployment section).
Get a free key at https://aistudio.google.com.
"""

import os
from google import genai

_client = None


def _get_client():
    """Lazily creates the Gemini client so the app can still start
    (dashboard, sensor ingestion, etc.) even without GEMINI_API_KEY set."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client

SYSTEM_PROMPT = (
    "You are a heart-rate monitoring assistant for university athletes and coaches. "
    "You give short, practical, safety-conscious recommendations based on the athlete "
    "data provided to you. You are not a doctor and must not diagnose medical conditions "
    "or prescribe treatment — for high-severity or unclear cases, recommend the athlete "
    "stop training and consult a medical professional. Keep responses to 2-4 sentences."
)


def _build_context(athlete_name: str, diagnosis: dict | None) -> str:
    if not diagnosis:
        return f"Athlete: {athlete_name}. No active alert — general question."

    return (
        f"Athlete: {athlete_name}\n"
        f"Alert classification: {diagnosis['classification']}\n"
        f"Severity: {diagnosis['severity']}\n"
        f"Explanation: {diagnosis['explanation']}\n"
        f"Recent BPM readings: {diagnosis['recent_bpms']}"
    )


def get_recommendation(athlete_name: str, diagnosis: dict | None, user_message: str | None = None) -> str:
    """
    Called either:
    - automatically right after run_diagnosis(), with user_message=None, to
      generate the alert's recommendation text, or
    - from the /chat endpoint, with a user_message, for follow-up questions.
    """
    context = _build_context(athlete_name, diagnosis)
    prompt = user_message or "Give a short recommendation based on this alert."

    response = _get_client().models.generate_content(
        model="gemini-3.6-flash",
        contents=f"{context}\n\nQuestion: {prompt}",
        config={"system_instruction": SYSTEM_PROMPT},
    )

    return response.text
