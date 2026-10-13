# Project361 Integrated Backend

This version keeps the integrated AI/ML backend and adds Sandra's Firebase Admin authentication, Firestore/Realtime Database support, and CORS.

## Setup
1. Create a virtual environment.
2. Install `pip install -r requirements.txt`.
3. Copy Sandra's `serviceAccountKey.json` into this folder (do not commit/share it).
4. Create `.env` with `FIREBASE_PROJECT_ID`, `FIREBASE_DATABASE_URL`, and `FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json`.
5. Run `python app.py` (port 5000).

The frontend sends the Firebase ID token as `Authorization: Bearer <token>`. ESP32 may continue using `X-Device-Token`.
