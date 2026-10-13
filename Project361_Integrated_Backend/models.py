"""
models.py

SQLite data layer for the AI-Driven Heart Rate Monitoring backend.
Kept as plain sqlite3 (no ORM) to match the Milestone 1 design, which
specifies SQLite as the prototype database.

Tables:
    athletes        - athlete profile + HR baseline (resting/max)
    hr_readings      - one row per incoming sensor reading
    alerts          - raised when a reading is flagged anomalous
    diagnoses       - detailed diagnosis generated when an alert fires
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "heart_rate.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS athletes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER,
                resting_hr INTEGER DEFAULT 60,
                max_hr INTEGER DEFAULT 190
            );

            CREATE TABLE IF NOT EXISTS hr_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                bpm INTEGER NOT NULL,
                zone INTEGER,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                reading_id INTEGER,
                severity TEXT,
                message TEXT,
                acknowledged INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id),
                FOREIGN KEY (reading_id) REFERENCES hr_readings(id)
            );

            CREATE TABLE IF NOT EXISTS diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                athlete_id INTEGER NOT NULL,
                classification TEXT,
                severity TEXT,
                explanation TEXT,
                recommendation TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (alert_id) REFERENCES alerts(id),
                FOREIGN KEY (athlete_id) REFERENCES athletes(id)
            );
            """
        )


def seed_demo_athlete():
    """Creates one demo athlete if the table is empty, so /dashboard has data to show."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM athletes LIMIT 1").fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO athletes (name, age, resting_hr, max_hr) VALUES (?, ?, ?, ?)",
                ("Demo Athlete", 21, 62, 195),
            )
