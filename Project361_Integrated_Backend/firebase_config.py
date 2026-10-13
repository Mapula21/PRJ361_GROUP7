"""
firebase_config.py

Initialises the Firebase Admin SDK and exports clients for Firestore,
Realtime Database, and Authentication. Falls back gracefully to local
SQLite when Firebase credentials are not present (development mode).

Services available:
    - Firestore (NoSQL, for athletes/readings/alerts/diagnoses)
    - Realtime Database (JSON tree, streaming-friendly for live HR data)
    - Authentication (verify Firebase ID tokens from web/Flutter clients)

Setup:
    1. Download service account key from Firebase Console
       (Project Settings > Service Accounts > Generate New Private Key)
       and save it as 'serviceAccountKey.json' in the project root.
    2. Set FIREBASE_PROJECT_ID, FIREBASE_DATABASE_URL and
       FIREBASE_CREDENTIALS_PATH in .env
    3. In Firebase Console, enable the Realtime Database and
       Authentication services for the project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

_firestore = None
_rtdb = None
_auth = None
_firebase_app = None
_firebase_available = False


def init_firebase():
    """
    Initialises Firebase Admin SDK (Firestore + Realtime DB + Auth).
    Returns True if Firebase is ready, False if it falls back to SQLite.
    """
    global _firestore, _rtdb, _auth, _firebase_app, _firebase_available

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, db as rtdb, auth

        project_id = os.environ.get("FIREBASE_PROJECT_ID")
        cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
        cred_full = Path(__file__).parent / cred_path
        database_url = os.environ.get("FIREBASE_DATABASE_URL") or ""

        if not (cred_full.exists() and project_id):
            print("[firebase_config] Firebase credentials missing — falling back to SQLite.")
            _firebase_available = False
            return False

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(cred_full))
            app_args = {"projectId": project_id}
            if database_url:
                app_args["databaseURL"] = database_url
            _firebase_app = firebase_admin.initialize_app(cred, app_args)
        else:
            _firebase_app = firebase_admin.get_app()

        _firestore = firestore.client(_firebase_app)
        _auth = auth
        _firebase_available = True
        print("[firebase_config] Firebase initialised (Firestore + Auth).")

        if database_url:
            try:
                _rtdb = rtdb
                # Light connectivity probe
                import firebase_admin.db
                print("[firebase_config] Realtime Database URL configured:", database_url)
            except Exception as exc:
                print(f"[firebase_config] Realtime DB init warning: {exc}")
                _rtdb = None

        return True

    except Exception as exc:
        print(f"[firebase_config] Firebase init failed ({exc}) — falling back to SQLite.")
        _firebase_available = False
        return False


def get_firestore():
    """Returns the Firestore client, or None if Firebase is unavailable."""
    return _firestore if _firebase_available else None


def get_rtdb():
    """Returns the Realtime Database module reference, or None if unavailable."""
    return _rtdb if _firebase_available else None


def get_auth():
    """Returns the Firebase Auth module reference, or None if unavailable."""
    return _auth if _firebase_available else None


def is_firebase_available():
    """Returns True if Firebase was initialised successfully."""
    return _firebase_available
