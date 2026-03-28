# Healthcare Guiding Badge (MERN)

This project now includes a full MERN-style web application based on the original Heart Tag RFID lookup UI.

## Structure

- `client/` React + Vite frontend
- `server/` Express + Mongoose backend API
- `heart-tag-ui.html` original standalone prototype (kept for reference)

## Features

- RFID patient lookup UI in React + TypeScript
- New Patient TXT Writer page for ESP32/RFID workflows
- Express REST API endpoints:
  - `GET /api/health`
  - `GET /api/patients`
  - `GET /api/patients/rfid/:rfid`
	- `POST /api/patients/txt`
- MongoDB integration via Mongoose
- Mock fallback data if MongoDB is not running

## Setup

1. Install dependencies:
	- `npm install`
	- `npm install --prefix server`
	- `npm install --prefix client`
2. Configure backend env:
	- copy `server/.env.example` to `server/.env`
	- set `MONGODB_URI` as needed
3. Start full stack:
	- `npm run dev`
4. Open frontend:
	- `http://localhost:5173`

## TXT Writer Output

- The Patient TXT Writer page saves files in `RFID Code/patients/`.
- File format matches the ESP32-friendly key-value script style (for example: `id:`, `name:`, `allergy:`, `symptom:` lines).

## Notes

- If MongoDB is not available, the API still runs using fallback mock patient records.
- Hardware-related folders (`RFID Code/`, `ProcessVoice/`, `3d Files/`) remain unchanged.