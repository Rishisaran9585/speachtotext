# Vox — Speech to Text

A multilingual live speech-to-text application for the Procucev AI Tech hiring assignment. React/Vite frontend, FastAPI backend, faster-whisper transcription, and PostgreSQL persistence (SQLite locally).

## Features
- Live microphone capture with segmented audio uploads
- Multilingual Whisper transcription and language detection
- Transcript history, search, edit, and delete
- PostgreSQL on Render, SQLite for local development
- FastAPI health endpoint and CRUD tests

## Run locally
Backend: `cd backend && python -m venv .venv && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`
Frontend: `cd frontend && npm install && npm run dev`
Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` if frontend and API use different origins. First transcription downloads the selected Whisper model. Browser microphone access requires HTTPS in production.

## Tests
`cd backend && pytest -q`. Tests cover health, CRUD, and validation; they do not download the Whisper model.

## Render
Create a Blueprint from this repository using `render.yaml`. After the API service is live, set the static site's build-time `VITE_API_URL` to the API's public origin and redeploy the static site. Verify `/api/health` and microphone access. Set `CORS_ORIGINS` to the frontend origin for production. The app has no authentication; do not store sensitive transcripts.
