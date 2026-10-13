# PRJ361 HeartRate+ Web Application — Frontend Prototype

This is the first frontend build for the Project361 heart-rate monitoring system.

## Current scope
- Athlete dashboard
- Current BPM
- Heart-rate zone
- Fatigue score
- Risk level
- Heart-rate trend chart
- AI recommendation area
- Recent alerts
- Session summary
- Session history
- Alerts page
- Athlete profile
- Responsive layout
- AI assistant UI placeholder

## Current data
The interface uses dummy/demo data so development can continue while the group finalises Firebase/Supabase and Flask integration.

## Planned integration
The current Lindo backend exposes a Flask dashboard/API structure including:
- POST /heartrate
- GET /analytics
- GET /alerts
- POST /chat
- GET /dashboard

The frontend should be connected to the final agreed architecture after the group confirms whether Flask remains the API layer and whether the persistent database is Firebase or Supabase.

## Run
Open `index.html` in a browser, or serve the folder with a local web server.
